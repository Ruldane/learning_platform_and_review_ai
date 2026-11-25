"""The question asked to January and the reading of her answer (SPEC F10, 9.4, D145).

`ask` only does `interrupt()` then rereads the answer (pure, no port or model): alone in its
node, replayed from its beginning on resume, it asks the same question again, the one in the
state.

Question (`kind = "interview_answer"`): `question` is the text asked (the main question, or its
follow-up); `fields` a single text field `answer` (4,000 characters); `options` a single one,
`stop` ("End the interview"). Answer: `{"answers": {"answer": text}}`, or `"stop"` (or
`{"action": "stop"}`). An unreadable answer (empty text, unknown shape) asks the same question
again.

`turn` reads the answer (inside `untrusted`): an internal score from 1 to 5 and, at most once
per question, a follow-up that goes back through `ask`. A silent or too slow model
(`RECOVERABLE_CODES`) does not make the interview fail: neutral score, no follow-up. The
exchanges stay in the state until `save`."""

import asyncio
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from app.agents.nodes.interviewer.common import (
    AGENT,
    RECOVERABLE_CODES,
    Node,
    context_of,
    say_question,
)
from app.agents.nodes.interviewer.context import exchange_text, head_vars
from app.agents.nodes.interviewer.salary import salary_decision
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.interview import InterviewState
from app.agents.tools.interview_schema import (
    Exchange,
    InterviewContext,
    PlannedQuestion,
    TurnDecision,
)
from app.core.errors import AppError

KIND = "interview_answer"
STOP = "stop"
STOP_LABEL = "End the interview"
ANSWER_FIELD = {"id": "answer", "label": "Your answer", "required": True, "max_length": 4000}
MAX_ANSWER_CHARS = 4000
TURN_REQUEST = "Read and score the answer."
TURN_CALL_TIMEOUT_S = 105.0  # shorter than a node's cap (120 s): the fallback gets written
NEUTRAL_NOTE = 3
CRITERION_LABELS = {
    "clarity": "clarity",
    "structure": "structure",
    "technical_depth": "technical depth",
    "role_fit": "fit for the role",
}

logger = logging.getLogger(__name__)


def question_payload(state: InterviewState) -> dict[str, Any]:
    return {
        "kind": KIND,
        "question": state["current"],
        "options": [{"value": STOP, "label": STOP_LABEL}],
        "fields": [ANSWER_FIELD],
    }


def parse_reply(value: Any) -> dict[str, Any] | None:
    """`{"action": "answer", "text"}`, `{"action": "stop"}` or `None` (asked again)."""
    if value == STOP or (isinstance(value, dict) and value.get("action") == STOP):
        return {"action": STOP}
    answers = value.get("answers") if isinstance(value, dict) else None
    text = answers.get("answer") if isinstance(answers, dict) else None
    if isinstance(text, str) and text.strip():
        return {"action": "answer", "text": text.strip()[:MAX_ANSWER_CHARS]}
    return None


def ask(state: InterviewState) -> InterviewState:
    """Stop point: the current question. Nothing before `interrupt()`."""
    return {"reply": parse_reply(interrupt(question_payload(state)))}


def route_ask(state: InterviewState) -> str:
    reply = state.get("reply")
    if reply is None:
        return "ask"
    return "debrief" if reply["action"] == STOP else "turn"


def route_turn(state: InterviewState) -> str:
    """A question remains to be asked (the follow-up, or the next one), otherwise the debrief."""
    return "debrief" if state["position"] >= len(state["plan"]) else "ask"


def _previous(state: InterviewState) -> str:
    """The exchange of the current question up to its follow-up (which awaits its score)."""
    last = Exchange.model_validate(state["exchanges"][-1])
    return untrusted(
        exchange_text(last, with_note=False, pending_follow_up=True), "previous exchange"
    )


def turn_vars(
    ctx: InterviewContext, planned: PlannedQuestion, state: InterviewState, text: str
) -> dict[str, Any]:
    final = state["follow_up_open"]
    return {
        **head_vars(ctx),
        "mode": "turn",
        "final": final,
        "criterion_label": CRITERION_LABELS[planned.criterion],
        "question": untrusted(planned.text, "interview question"),
        "answer": untrusted(text, "January's answer"),
        "before": _previous(state) if final else "",
    }


async def _decide(
    deps: GraphDeps, state: InterviewState, planned: PlannedQuestion, text: str
) -> tuple[TurnDecision, bool]:
    """The model's decision, and whether it is a fallback; without a readable answer in time:
    neutral score, no follow-up."""
    step = f"tour-{state['position'] + 1}" + ("-relance" if state["follow_up_open"] else "")
    prompt = render_prompt(AGENT, **turn_vars(context_of(state), planned, state, text))
    try:
        async with asyncio.timeout(TURN_CALL_TIMEOUT_S):
            model = await deps.models.get_chat_model(
                deps.user_id, get_agent(AGENT).tier, agent=AGENT
            )
            decision = await structured_call(
                model,
                TurnDecision,
                [SystemMessage(prompt), HumanMessage(TURN_REQUEST)],
                agent=AGENT,
                step=step,
                intent="Reading your answer.",
            )
            return decision, False
    except (AppError, TimeoutError) as exc:
        code = exc.code if isinstance(exc, AppError) else "timeout"
        if code != "timeout" and code not in RECOVERABLE_CODES:
            raise
        logger.warning(
            "Interviewer without a model answer (%s), neutral score: session %s, %s",
            code,
            deps.session_id,
            step,
        )
        return TurnDecision(follow_up=None, note=NEUTRAL_NOTE), True


def _answered(
    state: InterviewState,
    planned: PlannedQuestion,
    text: str,
    decision: TurnDecision,
    fallback: bool,
) -> list[dict[str, Any]]:
    """The exchanges with this answer: the answered follow-up completes the last exchange (as a
    fallback, the first answer's score stays); otherwise a new exchange (the follow-up, if
    there is one, awaits its answer)."""
    exchanges = list(state["exchanges"])
    if state["follow_up_open"]:
        last = {**exchanges[-1], "follow_up_answer": text}
        if not fallback:
            last["note"] = decision.note
        return [*exchanges[:-1], last]
    exchange = Exchange(
        index=state["position"],
        question=planned.text,
        criterion=planned.criterion,
        source=planned.source,
        answer=text,
        follow_up=decision.follow_up,
        note=decision.note,
        unrated=fallback,
        salary_raised=decision.salary_move,
    )
    return [*exchanges, exchange.model_dump()]


def make_turn(deps: GraphDeps) -> Node:
    @node_timeout()
    async def turn(state: InterviewState) -> InterviewState:
        """Scores the answer; one follow-up at most per question, otherwise the next question."""
        reply = state["reply"]
        if reply is None or reply["action"] != "answer":  # `route_ask` does not send it here
            raise RuntimeError("`turn` expects an answer read by `ask`")
        planned = PlannedQuestion.model_validate(state["plan"][state["position"]])
        decision, fallback = await _decide(deps, state, planned, reply["text"])
        context = context_of(state)
        decision = salary_decision(state, context, decision)
        if context.surprise:
            decision = decision.model_copy(update={"follow_up": None})
        exchanges = _answered(state, planned, reply["text"], decision, fallback)
        position = state["position"]
        logger.info("Answer scored: session %s, question %d", deps.session_id, position + 1)
        if not state["follow_up_open"] and decision.follow_up:
            say_question(position + 1, decision.follow_up, follow_up=True)
            return {"exchanges": exchanges, "current": decision.follow_up, "follow_up_open": True}
        position += 1
        current = ""
        if position < len(state["plan"]):
            current = state["plan"][position]["text"]
            say_question(position + 1, current)
        return {
            "exchanges": exchanges,
            "position": position,
            "current": current,
            "follow_up_open": False,
        }

    return turn
