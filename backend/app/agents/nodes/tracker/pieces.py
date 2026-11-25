"""Prepare the application kit pieces handled by the Tracker (SPEC 6.4, F16, D142).

The résumé branch uses the latest ready version. The other branches draft text from
the profile, posting, application, and style guide, supplied as untrusted data.
`honesty` checks claims and word counts. One retry names the issues to fix. A piece
that still needs review records `to_check` with any unsupported terms in `meta.flags`
and word counts in `meta.words`. Salary answers and answers without valid supporting
facts are cleared. Each branch can fail independently.
"""

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.nodes.tracker.honesty import (
    Review,
    fix_answers,
    meta_words,
    retry_message,
    review,
)
from app.agents.nodes.tracker.intake import AGENT
from app.agents.nodes.tracker.kit_common import Node, Piece, finish, guarded
from app.agents.nodes.tracker.kit_prompt import prompt_vars
from app.agents.prompts.loader import render_prompt
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.application_kit import ApplicationKitState
from app.agents.tools.cv_schema import facts_of
from app.agents.tools.kit_schema import (
    Draft,
    Followups,
    FormAnswers,
    KitContext,
    KitKind,
    KitStatus,
    Letter,
    LinkedInMessages,
    Pitch,
)
from app.core.errors import AppError

PIECE_LIMIT_S = 240  # At most two requests, each with its own provider retries.
NO_CV = "Run the résumé review for this posting to create a tailored résumé."


@dataclass(frozen=True)
class TextSpec:
    kind: KitKind
    schema: type[Draft]
    request: str
    intent: str


SPECS: dict[str, TextSpec] = {
    spec.kind: spec
    for spec in (
        TextSpec("letter", Letter, "Write the cover letter.", "writing the cover letter"),
        TextSpec(
            "linkedin", LinkedInMessages, "Write the LinkedIn invitation and message.",
            "writing the LinkedIn messages",
        ),
        TextSpec(
            "followups", Followups, "Write the two follow-up emails.",
            "writing the follow-up emails",
        ),
        TextSpec("pitch", Pitch, "Write the elevator pitch.", "writing the elevator pitch"),
        TextSpec(
            "form_answers", FormAnswers, "Answer the screening questions.",
            "preparing the form answers",
        ),
    )
}  # fmt: skip


@dataclass(frozen=True)
class Written:
    draft: Draft
    found: Review  # Issues that remain after the retry.


def _fixed(draft: Draft, ctx: KitContext) -> Draft:
    """Check the form's fact IDs and clear answers that should be left blank."""
    if isinstance(draft, FormAnswers):
        return fix_answers(draft, set(facts_of(ctx.profile)))
    return draft


async def write(deps: GraphDeps, ctx: KitContext, spec: TextSpec) -> Written:
    """Draft and check the piece, with one retry that names the issues."""
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    prompt = render_prompt(AGENT, mode=spec.kind, **prompt_vars(ctx, deps.settings.style_guide))
    messages = [SystemMessage(prompt), HumanMessage(spec.request)]

    async def ask(conversation: list[Any]) -> Draft:
        return await structured_call(
            model, spec.schema, conversation, agent=AGENT, step=spec.kind, intent=spec.intent
        )

    first = await ask(messages)
    draft = _fixed(first, ctx)
    found = review(draft, ctx)
    if not found:
        return Written(draft, found)
    retry = [*messages, AIMessage(first.model_dump_json()), HumanMessage(retry_message(found))]
    try:
        again = _fixed(await ask(retry), ctx)
    except AppError as exc:
        if exc.code != "structured_output_invalid":
            raise
        return Written(draft, found)  # If the retry cannot be parsed, keep the draft for review.
    return Written(again, review(again, ctx))


def piece_of(written: Written) -> Piece:
    """Save a ready piece or flag the draft for the user's review."""
    draft = written.draft
    meta: dict[str, Any] = {"language": "en"}
    words = meta_words(draft)
    if words is not None:
        meta["words"] = words
    if written.found.terms:
        meta["flags"] = written.found.terms
    blank = False
    if isinstance(draft, FormAnswers):
        states = [item.state for item in draft.items]
        meta["items"] = [
            {"question": i.question, "answer": i.answer, "fact_ids": i.fact_ids, "state": i.state}
            for i in draft.items
        ]
        meta["salary"] = "salary" in states
        blank = any(state != "ok" for state in states)
    status: KitStatus = "to_check" if written.found or blank else "ready"
    return Piece(status, draft.render(), meta)


def make_text_piece(deps: GraphDeps, kind: str) -> Node:
    spec = SPECS[kind]

    async def piece(state: ApplicationKitState) -> ApplicationKitState:
        ctx = await deps.ports.kit.context(deps.user_id, state["application_id"])

        async def work() -> Piece:
            return piece_of(await write(deps, ctx, spec))

        done = await guarded(PIECE_LIMIT_S, work)
        return await finish(deps, ctx.application_id, spec.kind, done, agent=AGENT)

    piece.__name__ = f"piece_{kind}"
    return node_timeout(PIECE_LIMIT_S + 60)(piece)


def make_cv(deps: GraphDeps) -> Node:
    @node_timeout()
    async def cv(state: ApplicationKitState) -> ApplicationKitState:
        """Point to the posting's latest ready résumé version."""
        ctx = await deps.ports.kit.context(deps.user_id, state["application_id"])
        version = ctx.cv_version
        if version is None:
            done = Piece("to_check", NO_CV)
        else:
            content = f"Tailored résumé (version {version.number})"
            done = Piece("ready", content, {"version_id": version.version_id})
        return await finish(deps, ctx.application_id, "cv", done, agent=AGENT)

    return cv
