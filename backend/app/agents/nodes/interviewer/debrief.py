"""The interview debrief and its filing (SPEC F10, 1, 18.3, D145).

`debrief` gives the exchanges (inside `untrusted`) to the Interviewer: four scores, three
strengths, three fixes, the improved version of the weakest answer and the expected points of
the missed questions. The code decides what counts: the weakest answer is the one with the
lowest internal score (the oldest on a tie), the missed questions those whose score is 2 at
most; the model writes, it does not choose. The improved answer is written in January's name:
`text_claims` flags what her profile does not state (`flags`), the answer is shown "to
verify". Stopped before any answer: no call, no debrief (`stopped`).

`save` files the outcome through the port, idempotent per session (SPEC 9.4): the only node
that writes. One review card per missed question: the question on the front, the points of a
good answer on the back. The debrief never makes the answers get lost: if it fails (unreadable
answer after the retries, transient failure, slowness: `RECOVERABLE_CODES`, or
`DEBRIEF_CALL_TIMEOUT_S`), `save` still files the exchanges with `debrief=None`, without
cards, and tells January; interview `debrief_failed` on the port side (non-empty exchanges, no
debrief), distinct from `stopped` (empty exchanges). The token cap (`token_cap_reached`) and the
other errors stop the session.
Logs: identifiers and numbers only (17.2)."""

import asyncio
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.nodes.interviewer.common import AGENT, RECOVERABLE_CODES, Node, context_of
from app.agents.nodes.interviewer.context import exchanges_block, head_vars, profile_block
from app.agents.nodes.interviewer.salary import without_unsourced_figures
from app.agents.prompts.loader import render_prompt
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.prose import shorten
from app.agents.runtime.structured import structured_call
from app.agents.state.interview import InterviewState
from app.agents.tools.interview_schema import (
    Debrief,
    Exchange,
    ExpectedPoints,
    InterviewContext,
    debrief_schema,
)
from app.agents.tools.study_schema import CardDraft
from app.agents.tools.text_claims import text_claims
from app.core.errors import AppError

DEBRIEF_REQUEST = "Write the interview debrief."
DEBRIEF_TIMEOUT_S = 300  # node cap (`node_timeout`)
DEBRIEF_CALL_TIMEOUT_S = 270.0  # shorter: the fallback (nothing to write) has margin
MISSED_MAX_NOTE = 2
FRONT_MAX = 300
NOTHING_TO_GRADE = "Interview ended. No answers to score."
DEBRIEF_FAILED = (
    "The debrief couldn't be written. Your answers are saved. No scores or review cards were made."
)

logger = logging.getLogger(__name__)


def weakest_index(exchanges: list[Exchange]) -> int:
    """The question with the lowest internal score (an ungraded answer comes after), the oldest
    on a tie."""
    return min(exchanges, key=lambda e: (e.unrated, e.note, e.index)).index


def missed_indices(exchanges: list[Exchange]) -> list[int]:
    return [e.index for e in exchanges if e.note <= MISSED_MAX_NOTE]


def allowed_phrases(ctx: InterviewContext) -> list[str]:
    """The whole phrases that the answer may write: the company and the job title,
    never a tool or a figure from the posting."""
    names = [ctx.role]
    if ctx.analysis is not None:
        names += [ctx.analysis.company or "", ctx.analysis.title]
    return list(dict.fromkeys(name for name in names if name))


def flagged_terms(text: str, ctx: InterviewContext) -> list[str]:
    """The terms the profile does not state, without duplicates, in the order of the text."""
    claims = text_claims(text, ctx.profile, allowed=allowed_phrases(ctx))
    return list(dict.fromkeys(claim.term for claim in claims))


def revision_cards(exchanges: list[Exchange], debrief: Debrief) -> list[CardDraft]:
    """One card per missed question: question on the front, a good answer's points on the back."""
    points = {item.index: item.points for item in debrief.expected}
    by_index = {e.index: e for e in exchanges}
    return [
        CardDraft(
            front=shorten(by_index[index].question, FRONT_MAX),
            back="\n".join(f"- {point}" for point in points[index]),
        )
        for index in debrief.missed
        if index in by_index and index in points
    ]


def debrief_vars(
    ctx: InterviewContext, exchanges: list[Exchange], weakest: int, missed: list[int]
) -> dict[str, object]:
    return {
        **head_vars(ctx),
        "mode": "debrief",
        "answered": len(exchanges),
        "exchanges": exchanges_block(exchanges),
        "profile": profile_block(ctx),
        "weakest": weakest,
        "missed": ", ".join(str(index) for index in missed) or "none",
    }


def _once_each(items: list[ExpectedPoints], missed: list[int]) -> list[ExpectedPoints]:
    """The points of the missed questions only, once each (the first one wins)."""
    first: dict[int, ExpectedPoints] = {}
    for item in items:
        if item.index in missed:
            first.setdefault(item.index, item)
    return [first[index] for index in missed if index in first]


async def _written(deps: GraphDeps, ctx: InterviewContext, exchanges: list[Exchange]) -> Debrief:
    weakest, missed = weakest_index(exchanges), missed_indices(exchanges)
    prompt = render_prompt(AGENT, **debrief_vars(ctx, exchanges, weakest, missed))
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    found = await structured_call(
        model,
        debrief_schema(missed),
        [SystemMessage(prompt), HumanMessage(DEBRIEF_REQUEST)],
        agent=AGENT,
        step="debrief",
        intent="Writing your debrief.",
    )
    update = {
        "weakest_index": weakest,
        "missed": missed,
        "expected": _once_each(found.expected, missed),
        "unrated": [e.index for e in exchanges if e.unrated],
    }
    return Debrief.model_validate(found.model_copy(update=update).model_dump())


async def _try_written(
    deps: GraphDeps, ctx: InterviewContext, exchanges: list[Exchange]
) -> Debrief | None:
    """The debrief, or `None` if the model did not answer in time or readably: January's answers
    are not lost. The other errors (including the token cap) bubble up."""
    try:
        async with asyncio.timeout(DEBRIEF_CALL_TIMEOUT_S):
            return await _written(deps, ctx, exchanges)
    except (AppError, TimeoutError) as exc:
        code = exc.code if isinstance(exc, AppError) else "timeout"
        if code != "timeout" and code not in RECOVERABLE_CODES:
            raise
        logger.warning(
            "Interviewer without debrief (%s), answers kept: session %s, %d exchange(s)",
            code,
            deps.session_id,
            len(exchanges),
        )
        return None


def make_debrief(deps: GraphDeps) -> Node:
    @node_timeout(DEBRIEF_TIMEOUT_S)
    async def debrief(state: InterviewState) -> InterviewState:
        """The debrief of the answered questions; no answer: no call, no debrief."""
        exchanges = [Exchange.model_validate(e) for e in state["exchanges"]]
        if not exchanges:
            return {"debrief": None, "flags": [], "cards": []}
        ctx = context_of(state)
        written = await _try_written(deps, ctx, exchanges)
        if written is None:  # the answers are filed without debrief (`save`)
            return {"debrief": None, "flags": [], "cards": []}
        if ctx.salary is not None:
            written = without_unsourced_figures(written, ctx.language)
        flags = flagged_terms(written.improved_answer, ctx)
        cards = [] if ctx.salary is not None else revision_cards(exchanges, written)
        logger.info(
            "Debrief written: session %s, %d question(s), %d missed, %d term(s) flagged",
            deps.session_id,
            len(exchanges),
            len(written.missed),
            len(flags),
        )
        return {
            "debrief": written.model_dump(),
            "flags": flags,
            "cards": [card.model_dump() for card in cards],
        }

    return debrief


def _closing(debrief: Debrief | None, cards: list[CardDraft], answered: int) -> str:
    if debrief is None:  # without an answer: stopped; with answers: debrief failed
        return DEBRIEF_FAILED if answered else NOTHING_TO_GRADE
    unscored = len(debrief.unrated)
    scored = answered - unscored
    questions = "question" if scored == 1 else "questions"
    text = f"Interview complete. {scored} {questions} scored. Your debrief is ready."
    if cards:
        noun = "card" if len(cards) == 1 else "cards"
        text += f" {len(cards)} review {noun} created."
    if unscored:
        answers = "answer" if unscored == 1 else "answers"
        text += f" {unscored} {answers} could not be scored."
    return text


def make_save(deps: GraphDeps) -> Node:
    @node_timeout()
    async def save(state: InterviewState) -> InterviewState:
        """The interview outcome, the only write; replayed, the port rereads the session's."""
        exchanges = [Exchange.model_validate(e) for e in state["exchanges"]]
        raw = state["debrief"]
        debrief = None if raw is None else Debrief.model_validate(raw)
        cards = [CardDraft.model_validate(c) for c in state["cards"]]
        await deps.ports.interviews.save_result(
            deps.user_id,
            deps.session_id,
            state["interview_id"],
            exchanges,
            debrief,
            state["flags"],
            cards,
        )
        logger.info(
            "Interview filed: session %s, interview %s, %d exchange(s), %d card(s)",
            deps.session_id,
            state["interview_id"],
            len(exchanges),
            len(cards),
        )
        text = _closing(debrief, cards, len(exchanges))
        emit("agent.message", {"message_id": f"{AGENT}-fin", "text": text}, agent=AGENT)
        return {"summary": text}

    return save
