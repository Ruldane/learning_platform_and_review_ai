"""January's answers (D102): the question asked (stop point), then the verdict, a hint, the
solution or the skip.

`ask` only does `interrupt()` then reads the answer (pure): nothing before the stop (SPEC 9.4).
An unreadable answer asks the same question again. "I'm stuck" and "Skip" are options of the
question; the label of "I'm stuck" carries the hint count ("I'm stuck (1/3)"), then becomes
"Show the solution": the front end counts nothing (F15). January's answer is wrapped as
untrusted (SPEC 17.4): an instruction it contains does not change the verdict.
Silent or too slow model (`fallback`, D115): answer not graded (`skipped`), hint counted
without text; the session continues."""

import logging
from dataclasses import asdict
from typing import Any

from langgraph.types import interrupt

from app.agents.nodes.tutor.fallback import (
    NO_EXPECTED,
    NO_SOLUTION,
    UNCHECKED,
    hint_unavailable,
    try_tutor,
)
from app.agents.nodes.tutor.models import (
    ANSWER_LABEL,
    MAX_ANSWER_CHARS,
    MAX_HINTS,
    TUTOR_QUESTION,
    AnswerCheck,
    HintTurn,
    Node,
    context_of,
    lesson_prompt,
    outcome_record,
    parse_tutor_answer,
    say,
    section_text,
    tutor_prompt,
    whole_lesson,
)
from app.agents.prompts.loader import untrusted
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.state.study_session import StudySessionState

CHECK_REQUEST = "Evaluate the answer."
HINT_REQUEST = "Give the next hint."
REVEAL_LABEL = "Show the solution"
SKIP_OPTION = {"value": "skip", "label": "Skip"}
ANSWER_FIELD = {"id": "answer", "label": "Your answer", "max_length": MAX_ANSWER_CHARS}

logger = logging.getLogger(__name__)


def stuck_label(hints: int) -> str:
    """ "I'm stuck (n/3)" for the upcoming hint n; "Show the solution" once exhausted."""
    return REVEAL_LABEL if hints >= MAX_HINTS else f"I’m stuck ({hints + 1}/{MAX_HINTS})"


def question_payload(state: StudySessionState) -> dict[str, Any]:
    stuck = {"value": "stuck", "label": stuck_label(state.get("hints", 0))}
    return {
        "kind": TUTOR_QUESTION,
        "question": state["question"],
        "options": [stuck, SKIP_OPTION],
        "fields": [ANSWER_FIELD],
    }


def ask(state: StudySessionState) -> StudySessionState:
    """Stop point: the current question. Nothing before `interrupt()`."""
    answer = parse_tutor_answer(interrupt(question_payload(state)))
    if answer is None:
        return {"reply": None}
    if answer.action == "finish":
        return {"reply": asdict(answer), "ended_early": True}
    return {"reply": asdict(answer)}


def route_answer(state: StudySessionState) -> str:
    reply = state.get("reply")
    if reply is None:
        return "ask"
    action = reply["action"]
    if action == "stuck":
        return "hint" if state.get("hints", 0) < MAX_HINTS else "reveal"
    return {"answer": "check", "skip": "skip", "finish": "summarize"}[action]


def _key(state: StudySessionState) -> str:
    return f"{state['phase']}-{state.get('index', 0) + 1}"


def _reference(state: StudySessionState) -> str:
    """What is used to judge: the section, the exercise statement, or the whole lesson (final)."""
    context = context_of(state)
    if state["phase"] == "section":
        return lesson_prompt(section_text(context.sections[state["index"]]))
    if state["phase"] == "exercise":
        return lesson_prompt(f"## Exercise\n\n{context.exercise}")
    return whole_lesson(context)


def _item(state: StudySessionState) -> str:
    """Question and expected answer: written by the Tutor or taken from the lesson (untrusted)."""
    expected = state["expected"].strip() or NO_EXPECTED  # fallback final question (D115)
    text = f"Question: {state['question']}\nExpected answer: {expected}"
    return untrusted(text, "question")


def make_check(deps: GraphDeps) -> Node:
    @node_timeout()
    async def check(state: StudySessionState) -> StudySessionState:
        reply = state["reply"]
        assert reply is not None  # guaranteed by `route_answer`
        prompt = tutor_prompt(
            state,
            "check",
            reference=_reference(state),
            item=_item(state),
            answer=untrusted(reply["text"], ANSWER_LABEL),
        )
        found = await try_tutor(
            deps,
            AnswerCheck,
            prompt,
            CHECK_REQUEST,
            step=f"verdict-{_key(state)}",
            intent="I’m reading your answer",
        )
        # Without a model verdict: `skipped`, no card and no practice ticked (F13, D115).
        verdict = found.verdict if found else "skipped"
        say(state, found.feedback if found else UNCHECKED, f"tutor-retour-{_key(state)}")
        logger.info(
            "Answer judged: session %s, %s, verdict %s, %d hint(s)",
            deps.session_id,
            _key(state),
            verdict,
            state.get("hints", 0),
        )
        return {"outcomes": outcome_record(state, verdict, checked=found is not None)}

    return check


def _previous(hints: list[str]) -> str:
    if not hints:
        return "None yet."
    return untrusted("\n".join(f"{n}. {h}" for n, h in enumerate(hints, start=1)), "hints")


def make_hint(deps: GraphDeps) -> Node:
    @node_timeout()
    async def hint(state: StudySessionState) -> StudySessionState:
        """Graded hint: 1 a lead, 2 the method, 3 almost the answer; then the question is asked
        again, with the updated count."""
        level = state.get("hints", 0) + 1
        given = state.get("given_hints", [])
        prompt = tutor_prompt(
            state,
            "hint",
            level=level,
            reference=_reference(state),
            item=_item(state),
            previous=_previous(given),
        )
        found = await try_tutor(
            deps,
            HintTurn,
            prompt,
            HINT_REQUEST,
            step=f"indice-{_key(state)}-{level}",
            intent="I’m preparing a hint",
        )
        message_id = f"tutor-indice-{_key(state)}-{level}"
        if found is None:  # the hint counts: the solution stays three clicks away, no model
            say(state, hint_unavailable(level, MAX_HINTS), message_id)
            return {"hints": level, "given_hints": given}
        say(state, f"Hint {level} of {MAX_HINTS}\n\n{found.hint}", message_id)
        return {"hints": level, "given_hints": [*given, found.hint]}

    return hint


def reveal(state: StudySessionState) -> StudySessionState:
    """After three hints: the solution (the expected answer), and the question is settled. Without
    an expected answer (fallback final question): no invented solution, and no card."""
    expected = state["expected"].strip()
    text = f"Solution\n\n{expected}" if expected else NO_SOLUTION
    say(state, text, f"tutor-solution-{_key(state)}")
    return {"outcomes": outcome_record(state, "revealed")}


def skip(state: StudySessionState) -> StudySessionState:
    return {"outcomes": outcome_record(state, "skipped")}
