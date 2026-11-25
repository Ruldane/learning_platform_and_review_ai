"""End of session (D102): the "Finish the session" question (stop point), the Tutor's review
(no write), then the filing through the port and the closing message.

The session only ends through this question or through "Finish" (`finish` answer to any
question, 5.6): the time comes from the timer, the feature counts it. `wrap_up` is the only
write of the flow, idempotent (study session already `finished`: reread); the closing message
comes after. Logs: identifiers and numbers only (SPEC 17.2)."""

import asyncio
import logging
from dataclasses import asdict
from typing import Any

from langgraph.types import interrupt

from app.agents.nodes.tutor.models import (
    AGENT,
    FINISH_SESSION,
    Node,
    SessionSummary,
    ask_tutor,
    context_of,
    outcomes_prompt,
    parse_tutor_answer,
    say,
    tutor_prompt,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.state.study_session import StudySessionState
from app.agents.tools.study_port import Outcome, StudyFinished, StudyOutcome, exercise_done
from app.core.errors import AppError

FINISH_QUESTION = "Finish the session to save your study time and skill progress."
FINISH_OPTION = {"value": "finish", "label": "Finish the session"}
SUMMARY_REQUEST = "Write the session review."
# Shorter than the node cap (120 s): beyond it, the numeric review, never `node_timeout`.
SUMMARY_TIMEOUT_S = 90.0
LEVEL_NAMES = {
    "declared": "Declared",
    "in_progress": "In progress",
    "validated": "Validated",
    "proven": "Proven",
}
SAVE_TIMEOUT_S = 300  # the feature files time, tasks, cards, acquired skills and the journal

logger = logging.getLogger(__name__)


def ask_finish(state: StudySessionState) -> StudySessionState:
    """End stop point. Nothing before `interrupt()`; any answer other than `finish` asks
    the question again."""
    value = interrupt(
        {"kind": FINISH_SESSION, "question": FINISH_QUESTION, "options": [FINISH_OPTION]}
    )
    answer = parse_tutor_answer(value)
    finished = answer is not None and answer.action == "finish"
    return {"reply": asdict(answer) if finished and answer is not None else None}


def route_finish(state: StudySessionState) -> str:
    return "summarize" if state.get("reply") else "ask_finish"


def outcomes_of(state: StudySessionState) -> list[Outcome]:
    """The port's results; the state's `unchecked` mark does not enter them (D115 no. 17)."""
    return [
        Outcome(**{k: v for k, v in o.items() if k != "unchecked"})
        for o in state.get("outcomes", [])
    ]


def _fallback_summary(state: StudySessionState, outcomes: list[Outcome]) -> str:
    good = sum(1 for o in outcomes if o.verdict == "correct")
    text = f"Study session complete. You answered {good} of {len(outcomes)} questions correctly."
    unchecked = sum(1 for o in state.get("outcomes", []) if o.get("unchecked"))
    return text + (f" I couldn’t check {unchecked} of your answers." if unchecked else "")


def make_summarize(deps: GraphDeps) -> Node:
    @node_timeout()
    async def summarize(state: StudySessionState) -> StudySessionState:
        """The Tutor's review. Unreadable after its retries, provider error or timeout exceeded:
        a numeric review instead (the session does not fail on the last step; final review of
        phase 5, A-m1)."""
        outcomes = outcomes_of(state)
        prompt = tutor_prompt(
            state,
            "summary",
            outcomes=outcomes_prompt(state),
            ended_early=bool(state.get("ended_early")),
            exercise_done=exercise_done(outcomes),
        )
        try:
            async with asyncio.timeout(SUMMARY_TIMEOUT_S):
                found = await ask_tutor(
                    deps,
                    SessionSummary,
                    prompt,
                    SUMMARY_REQUEST,
                    step="bilan",
                    intent="I’m reviewing the session",
                )
        except (AppError, TimeoutError) as exc:
            code = exc.code if isinstance(exc, AppError) else "timeout"
            logger.warning(
                "Review unavailable (%s), numeric review: session %s", code, deps.session_id
            )
            return {"session_summary": _fallback_summary(state, outcomes)}
        return {"session_summary": found.summary}

    return summarize


def _closing(summary: str, done: StudyFinished) -> str:
    tasks = ", ".join(f"“{title}”" for title in done.tasks_done) or "none"
    skills = ", ".join(f"{name} ({LEVEL_NAMES.get(level, level)})" for name, level in done.skills)
    lines = [
        summary,
        "",
        f"Recorded {done.minutes} min of study time.",
        f"Tasks completed\n{tasks}.",
        f"Review cards created from your mistakes\n{done.flashcards_created}.",
    ]
    if skills:
        lines.append(f"Skills updated\n{skills}.")
    return "\n".join(lines)


def _finished_state(done: StudyFinished) -> dict[str, Any]:
    return {
        "minutes": done.minutes,
        "tasks_done": list(done.tasks_done),
        "flashcards_created": done.flashcards_created,
        "skills": [[name, level] for name, level in done.skills],
    }


def make_wrap_up(deps: GraphDeps) -> Node:
    @node_timeout(SAVE_TIMEOUT_S)
    async def wrap_up(state: StudySessionState) -> StudySessionState:
        """The end filed by the port (idempotent), then the closing message."""
        outcomes = outcomes_of(state)
        result = StudyOutcome(
            outcomes=outcomes,
            exercise_done=exercise_done(outcomes),
            ended_early=bool(state.get("ended_early")),
            summary=state["session_summary"],
        )
        study_id = state["study_session_id"]
        done = await deps.ports.study.finish(deps.user_id, deps.session_id, study_id, result)
        logger.info(
            "Study session filed: session %s, study %s, %d question(s), %d min, "
            "%d task(s), %d card(s)",
            deps.session_id,
            study_id,
            len(outcomes),
            done.minutes,
            len(done.tasks_done),
            done.flashcards_created,
        )
        say(state, _closing(state["session_summary"], done), f"{AGENT}-fin")
        title = context_of(state).module_title
        return {
            "finished": _finished_state(done),
            "summary": f"Study session complete for “{title}” ({done.minutes} min).",
        }

    return wrap_up
