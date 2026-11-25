"""The Analyst (SPEC 5.3 step 1, F8, D121): it analyzes a job posting and links its skills to
January's skill inventory. Flow `gap_analysis`.

`load` reads the posting through the port; a posting that is already analyzed (by another session
or a CV review) is never analyzed again. `analyze` refuses a text that is too short without any
call (`enough_text`, same bound as the route), asks for the analysis (posting text wrapped by
`untrusted`), has it checked (keywords exactly as written in the posting, mandatory requirements
linked to `skills`) and asks again twice at most, keeping the best answer; keywords still absent
are removed. A text that is not a posting is rejected (`reject`). `match` asks for the link
between the needs and the existing inventory, by identifiers; the code then computes the rows and
the score, and adds to the inventory the needs left without a link (`save_gap`).

No stop point. The port writes (`save_analysis`, `reject`, `save_gap`) are idempotent: a node
replayed after a stop (SPEC 9.4) writes nothing more.

Logs: identifiers and numbers only, never the posting text, a skill name, a title or a company
(17.2)."""

import logging
from typing import Protocol

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.agents.nodes.analyst_steps import (
    AGENT,
    ANALYZE_REQUEST,
    MATCH_REQUEST,
    MAX_ANALYZE_ASKS,
    MAX_POSTING_CHARS,
    NOT_A_POSTING,
    TOO_SHORT,
    Problem,
    analysis_problems,
    analyze_vars,
    better_answer,
    clean_matches,
    drop_absent_keywords,
    duplicate_text,
    duplicates_json,
    gap_text,
    match_vars,
    problems_text,
    saved_json,
)
from app.agents.prompts.loader import render_prompt
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.gap_analysis import GapAnalysisState
from app.agents.tools.gap_port import GapSaved, KnownSkill, SkillMatch, SkillMatches
from app.agents.tools.posting_schema import PostingAnalysis, enough_text

ANALYZE_TIMEOUT_S = 600  # three requests of a long analysis (GLM), with their retries
MATCH_TIMEOUT_S = 300
SAVE_TIMEOUT_S = 300  # the port indexes the `posting` memory item and looks for duplicates

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: GapAnalysisState) -> GapAnalysisState: ...


def _say(message_id: str, text: str) -> None:
    emit("agent.message", {"message_id": f"{AGENT}-{message_id}", "text": text}, agent=AGENT)


def make_load(deps: GraphDeps) -> Node:
    @node_timeout()
    async def load(state: GapAnalysisState) -> GapAnalysisState:
        view = await deps.ports.gap.posting(deps.user_id, state["posting_id"])
        reused = view.analysis is not None
        logger.info(
            "Posting read: session %s, posting %s, analysis already stored %s",
            deps.session_id,
            view.posting_id,
            reused,
        )
        analysis = view.analysis.model_dump(mode="json") if view.analysis else None
        return {"analysis": analysis, "reused": reused}

    return load


def route_load(state: GapAnalysisState) -> str:
    return "match" if state.get("analysis") else "analyze"


async def _ask_analysis(deps: GraphDeps, text: str) -> tuple[PostingAnalysis, list[Problem]]:
    """One request, then two re-requests at most; returns the best analysis (`better_answer`)
    and its problems."""
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    prompt = render_prompt(AGENT, **analyze_vars(text))
    messages: list[BaseMessage] = [SystemMessage(prompt), HumanMessage(ANALYZE_REQUEST)]
    best: tuple[PostingAnalysis, list[Problem]] | None = None
    for ask in range(1, MAX_ANALYZE_ASKS + 1):
        if best is not None:
            messages += [AIMessage(best[0].model_dump_json()), HumanMessage(problems_text(best[1]))]
        found = await structured_call(
            model,
            PostingAnalysis,
            messages,
            agent=AGENT,
            step=f"analyse-{ask}",
            intent="I am analyzing the posting" if ask == 1 else "I am revising the analysis",
        )
        best = better_answer(best, found, analysis_problems(found, text))
        if not best[1]:
            break
    assert best is not None
    return best


def make_analyze(deps: GraphDeps) -> Node:
    @node_timeout(ANALYZE_TIMEOUT_S)
    async def analyze(state: GapAnalysisState) -> GapAnalysisState:
        """The Analyst's analysis, checked; replayed, it asks again without writing anything."""
        view = await deps.ports.gap.posting(deps.user_id, state["posting_id"])
        if not enough_text(view.text):  # same bound as the route (review 6.5, m6): no call
            logger.info(
                "Posting too short: session %s, posting %s", deps.session_id, view.posting_id
            )
            return {"analysis": None, "reused": False, "rejection": TOO_SHORT}
        if len(view.text) > MAX_POSTING_CHARS:
            logger.info(
                "Posting truncated for the analysis: session %s, posting %s, %d of %d characters",
                deps.session_id,
                view.posting_id,
                MAX_POSTING_CHARS,
                len(view.text),
            )
        found, problems = await _ask_analysis(deps, view.text)
        analysis, dropped = drop_absent_keywords(found, view.text)
        if problems:
            logger.info(
                "Analysis kept with %d problem(s): session %s, posting %s, %d keyword(s) removed",
                len(problems),
                deps.session_id,
                view.posting_id,
                dropped,
            )
        return {"analysis": analysis.model_dump(mode="json"), "reused": False}

    return analyze


def route_analyze(state: GapAnalysisState) -> str:
    analysis = state.get("analysis") or {}
    return "save_analysis" if analysis.get("is_job_posting") else "reject"


def make_reject(deps: GraphDeps) -> Node:
    @node_timeout()
    async def reject(state: GapAnalysisState) -> GapAnalysisState:
        reason = state.get("rejection") or NOT_A_POSTING
        await deps.ports.gap.reject(deps.user_id, state["posting_id"], reason)
        logger.info(
            "Posting rejected: session %s, posting %s", deps.session_id, state["posting_id"]
        )
        _say("refus", reason)
        return {"summary": reason}

    return reject


def make_save_analysis(deps: GraphDeps) -> Node:
    @node_timeout(SAVE_TIMEOUT_S)
    async def save_analysis(state: GapAnalysisState) -> GapAnalysisState:
        """The first stored analysis wins: the rest reads the one that is in the database."""
        assert state["analysis"] is not None  # guaranteed by `route_analyze`
        found = PostingAnalysis.model_validate(state["analysis"])
        saved = await deps.ports.gap.save_analysis(
            deps.user_id, deps.session_id, state["posting_id"], found
        )
        logger.info(
            "Analysis stored: session %s, posting %s, first %s, %d duplicate(s)",
            deps.session_id,
            saved.posting_id,
            saved.first,
            len(saved.duplicates),
        )
        return {
            "analysis": saved.analysis.model_dump(mode="json"),
            "duplicates": duplicates_json(saved),
        }

    return save_analysis


async def _ask_matches(
    deps: GraphDeps, analysis: PostingAnalysis, known: list[KnownSkill]
) -> SkillMatches | None:
    """The link requested from the model; with no need or no inventory, no call."""
    if not analysis.skills or not known:
        return None
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    prompt = render_prompt(AGENT, **match_vars(analysis, known))
    return await structured_call(
        model,
        SkillMatches,
        [SystemMessage(prompt), HumanMessage(MATCH_REQUEST)],
        agent=AGENT,
        step="rattachement",
        intent="I am matching the posting requirements to your skills",
    )


def make_match(deps: GraphDeps) -> Node:
    @node_timeout(MATCH_TIMEOUT_S)
    async def match(state: GapAnalysisState) -> GapAnalysisState:
        assert state["analysis"] is not None  # guaranteed by `route_load` and `save_analysis`
        analysis = PostingAnalysis.model_validate(state["analysis"])
        known = await deps.ports.gap.known_skills(deps.user_id)
        found = await _ask_matches(deps, analysis, known)
        matches, unknown = clean_matches(analysis, found, known)
        logger.info(
            "Matching: session %s, posting %s, %d need(s), %d linked, %d answer(s) "
            "outside the needs or the inventory ignored",
            deps.session_id,
            state["posting_id"],
            len(matches),
            sum(m.known is not None for m in matches),
            unknown,
        )
        return {"matches": [m.model_dump() for m in matches]}

    return match


def make_save_gap(deps: GraphDeps) -> Node:
    @node_timeout(SAVE_TIMEOUT_S)
    async def save_gap(state: GapAnalysisState) -> GapAnalysisState:
        """Rows and score computed by the port code (idempotent per session)."""
        matches = [SkillMatch.model_validate(m) for m in state.get("matches", [])]
        saved = await deps.ports.gap.save_gap(
            deps.user_id, deps.session_id, state["posting_id"], matches
        )
        logger.info(
            "Gap stored: session %s, posting %s, score %d, %d row(s), %d missing",
            deps.session_id,
            state["posting_id"],
            saved.score,
            saved.rows,
            saved.missing,
        )
        return {"saved": saved_json(saved)}

    return save_gap


def announce(state: GapAnalysisState) -> GapAnalysisState:
    """The score, the missing skills, the possible duplicate, then the gap ready."""
    text = gap_text(GapSaved(**state["saved"]))
    _say("ecart", text)
    if duplicate := duplicate_text(state.get("duplicates", [])):
        _say("doublon", duplicate)
        text = f"{text} {duplicate}"
    posting_id = state["posting_id"]
    analysis = state["analysis"] or {}
    artifact = {
        "artifact_id": posting_id,
        "kind": "posting_gap",
        "title": str(analysis.get("title") or "Posting"),
        "url": f"/career/postings/{posting_id}",
    }
    emit("artifact.ready", artifact, agent=AGENT)
    return {"summary": text}
