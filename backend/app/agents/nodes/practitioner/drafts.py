"""The Practitioner writes the four drafts of a validated project (P3, P4, D165): a CV line, the
profile's project entry, a LinkedIn post and the README outline. A standard call, in January's
name: the code checks each text, never the model.

- `text_claims(draft_text(kind), project_reference(...), allowed=[statement title])`: the
  figures, tools, titles and proper names that neither the validated profile, nor what January
  says about her project, nor the module's skills state. The repository README is **never** a
  reference (web text) and is not shown to the model;
- the LinkedIn post is 80 to 200 words, counted by the code.

A faulty draft goes back to the model **only once**, with all the terms named (and the length);
drafts that are already clean are kept. What remains after the retry is stored "to verify" with
its terms (`flags`). The retry is a separate node (`redo`, its own timeout): any failure, of
whatever kind, keeps the first draft "to verify". The validated evaluation is not lost. The
first call also has its own timeout (`DRAFTS_BUDGET_S`): if it fails (provider, format, token
cap, timeout), the validated evaluation is stored **without drafts** ("drafts unavailable"),
never lost (D173, D165 no. 5).

Logs: identifiers and numbers, never a draft or a term (17.2)."""

import asyncio
import logging
from dataclasses import dataclass, replace
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.errors import GraphInterrupt

from app.agents.nodes.practitioner.outcome import from_state, to_state
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.project_review import Node, ProjectReviewState
from app.agents.tools.cv_schema import MasterProfileData
from app.agents.tools.project_port import DraftResult, ReviewInputs
from app.agents.tools.project_schema import (
    DRAFT_KINDS,
    LINKEDIN_WORDS,
    DraftKind,
    ProjectDrafts,
    draft_text,
    linkedin_words,
    project_fact,
    project_reference,
)
from app.agents.tools.text_claims import text_claims
from app.core.errors import AppError

__all__ = [
    "ASK",
    "Problems",
    "check",
    "make_drafts",
    "make_redo",
    "results_of",
    "retry_message",
    "route_drafts",
]

AGENT = "practitioner"
ASK = "Write the project drafts."
NONE = "(none)"
RETRY_BUDGET_S = 90.0  # its own timeout, shorter than `node_timeout` (120 s)
DRAFTS_BUDGET_S = 100.0  # the first call: its own timeout, under `node_timeout`
LANGUAGES = {"fr": "French", "en": "English"}
RETRY = (
    "Remove these unsupported terms: {terms}. Rewrite the affected drafts ({kinds}) using "
    "January's description, the module skills, and the brief title. Treat the brief objective "
    "as context only."
)
LENGTH_RETRY = "The LinkedIn post has {words} words. Use {low} to {high} words."

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Problems:
    terms: list[str]  # what the reference does not state
    words: int | None  # the LinkedIn post's words when out of bounds

    def __bool__(self) -> bool:
        return bool(self.terms or self.words is not None)

    def flags(self) -> list[str]:
        """The terms, then the post's length when it is out of bounds."""
        low, high = LINKEDIN_WORDS
        length = [] if self.words is None else [f"{self.words} words ({low} to {high} expected)"]
        return [*self.terms, *length]


def check(
    drafts: ProjectDrafts, reference: MasterProfileData, title: str
) -> dict[DraftKind, Problems]:
    """The problems of each draft, in the order of the types (empty: `bool(...)` false)."""
    found: dict[DraftKind, Problems] = {}
    low, high = LINKEDIN_WORDS
    for kind in DRAFT_KINDS:
        text = draft_text(kind, drafts)
        terms = list(dict.fromkeys(c.term for c in text_claims(text, reference, allowed=[title])))
        count = linkedin_words(text) if kind == "linkedin_post" else low
        found[kind] = Problems(terms, None if low <= count <= high else count)
    return found


def retry_message(found: dict[DraftKind, Problems]) -> str:
    """The retry: all the terms named, the post's length if it is out of bounds."""
    flagged = {kind: problems for kind, problems in found.items() if problems}
    terms = list(dict.fromkeys(term for problems in flagged.values() for term in problems.terms))
    parts = []
    if terms:
        kinds = ", ".join(kind for kind, problems in flagged.items() if problems.terms)
        parts.append(RETRY.format(terms=", ".join(terms), kinds=kinds))
    words = flagged["linkedin_post"].words if "linkedin_post" in flagged else None
    if words is not None:
        low, high = LINKEDIN_WORDS
        parts.append(LENGTH_RETRY.format(words=words, low=low, high=high))
    return "\n".join(parts)


def results_of(drafts: ProjectDrafts, found: dict[DraftKind, Problems]) -> list[DraftResult]:
    return [
        DraftResult(
            kind=kind,
            content=draft_text(kind, drafts),
            entry=drafts.profile_entry if kind == "profile_entry" else None,
            status="to_check" if found[kind] else "ready",
            flags=found[kind].flags(),
        )
        for kind in DRAFT_KINDS
    ]


def prompt_of(inputs: ReviewInputs) -> str:
    """Wrap evidence and context as untrusted data for the drafting prompt."""
    return render_prompt(
        AGENT,
        mode="project_drafts",
        title=untrusted(" ".join(inputs.brief.title.split()), "brief title"),
        objective=untrusted(" ".join(inputs.brief.objective.split()), "brief objective"),
        skills=untrusted(", ".join(inputs.skills) or NONE, "module skills"),
        description=untrusted(inputs.description or NONE, "January's description"),
        language=LANGUAGES[inputs.language],
    )


def _reference(inputs: ReviewInputs) -> MasterProfileData:
    fact = project_fact(inputs.brief.title, inputs.description, inputs.skills, inputs.repo_url)
    return project_reference(inputs.profile, fact, inputs.skills)


async def _model(deps: GraphDeps) -> BaseChatModel:
    return await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)


def _stored(
    state: ProjectReviewState, drafts: ProjectDrafts, found: dict[DraftKind, Problems]
) -> dict[str, Any]:
    outcome = from_state(state["outcome"])
    return to_state(replace(outcome, drafts=results_of(drafts, found)))


def make_drafts(deps: GraphDeps) -> Node:
    """The first draft, checked and stored in the state (`to_check` with its terms); the retry
    is a separate node (`redo`), with its own timeout (D165)."""

    @node_timeout()
    async def drafts(state: ProjectReviewState) -> ProjectReviewState:
        project_id = state["project_id"]
        inputs = await deps.ports.projects.review_inputs(deps.user_id, project_id)
        messages: list[BaseMessage] = [SystemMessage(prompt_of(inputs)), HumanMessage(ASK)]
        try:
            async with asyncio.timeout(DRAFTS_BUDGET_S):
                first = await structured_call(
                    await _model(deps),
                    ProjectDrafts,
                    messages,
                    agent=AGENT,
                    step="brouillons",
                    intent="writing the project drafts",
                )
        except GraphInterrupt:
            raise
        except Exception as exc:  # the drafts are optional: the validated evaluation stays
            logger.info(
                "Drafts impossible: session %s, project %s, cause %s",
                deps.session_id,
                project_id,
                _code(exc),
            )
            outcome = from_state(state["outcome"])
            return {"outcome": to_state(replace(outcome, drafts=[])), "retry_needed": False}
        found = check(first, _reference(inputs), inputs.brief.title)
        logger.info(
            "Drafts written: session %s, project %s, %d to verify before the retry",
            deps.session_id,
            project_id,
            sum(bool(problems) for problems in found.values()),
        )
        return {
            "outcome": _stored(state, first, found),
            "first_drafts": first.model_dump(),
            "retry_needed": any(found.values()),
        }

    return drafts


def route_drafts(state: ProjectReviewState) -> str:
    return "redo" if state.get("retry_needed") else "save"


def _code(exc: Exception) -> str:
    if isinstance(exc, TimeoutError):
        return "node_timeout"
    return exc.code if isinstance(exc, AppError) else type(exc).__name__


def make_redo(deps: GraphDeps) -> Node:
    @node_timeout()
    async def redo(state: ProjectReviewState) -> ProjectReviewState:
        """Keeps the first draft and the validated evaluation if the correction fails."""
        project_id = state["project_id"]
        inputs = await deps.ports.projects.review_inputs(deps.user_id, project_id)
        reference, title = _reference(inputs), inputs.brief.title
        first = ProjectDrafts.model_validate(state["first_drafts"])
        found = check(first, reference, title)
        if not any(found.values()):  # resume: nothing left to fix, no empty message to the model
            logger.info("Nothing to fix: session %s, project %s", deps.session_id, project_id)
            return {"outcome": _stored(state, first, found)}
        conversation: list[BaseMessage] = [
            SystemMessage(prompt_of(inputs)),
            HumanMessage(ASK),
            AIMessage(first.model_dump_json()),
            HumanMessage(retry_message(found)),
        ]
        try:
            async with asyncio.timeout(RETRY_BUDGET_S):
                second = await structured_call(
                    await _model(deps),
                    ProjectDrafts,
                    conversation,
                    agent=AGENT,
                    step="brouillons-2",
                    intent="revising the project drafts",
                )
        except GraphInterrupt:
            raise
        except Exception as exc:  # the first draft stays stored, `to_check`
            logger.info(
                "Drafts retry impossible: session %s, project %s, cause %s",
                deps.session_id,
                project_id,
                _code(exc),
            )
            return {}
        fixed: dict[str, Any] = {k: getattr(second, k) for k in found if found[k]}
        final = first.model_copy(update=fixed)
        again = check(final, reference, title)
        logger.info(
            "Drafts corrected: session %s, project %s, %d to verify",
            deps.session_id,
            project_id,
            sum(bool(problems) for problems in again.values()),
        )
        return {"outcome": _stored(state, final, again)}

    return redo
