"""Edge nodes of the `quiz` flow (D100): read the module or the attempt, file the quiz, its
failure or the grades, all through the `QuizStore` port, then announce the result.

Each port write is idempotent (key: the quiz, the attempt): a node replayed after a stop
(SPEC 9.4) returns the same thing without an extra row. The flow asks no question: no
`interrupt()`. Logs: identifiers and numbers only, never a question or an answer
(SPEC 17.2)."""

import logging
from dataclasses import asdict
from typing import Protocol

from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.state.quiz import QuizState
from app.agents.tools.quiz_port import (
    AttemptToGrade,
    GradedSaved,
    GradingItem,
    ModuleMaterial,
    QuizDraft,
    read_question_type,
)

AGENT = "examiner"
PASS_PERCENT = 80  # reminded to January; the rule itself lives in the feature (`scoring`)
SAVE_TIMEOUT_S = 300  # the port files the grade, the cards, the follow-up tasks and the journal

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: QuizState) -> QuizState: ...


def route_mode(state: QuizState) -> str:
    return "material" if state["mode"] == "generate" else "load_attempt"


def material_of(state: QuizState) -> ModuleMaterial:
    return ModuleMaterial(**state["material"])


def attempt_of(state: QuizState) -> AttemptToGrade:
    data = dict(state["attempt"])
    items = [
        GradingItem(**(item | {"type": read_question_type(item["type"])}))
        for item in data.pop("open_items")
    ]
    return AttemptToGrade(open_items=items, **data)


def make_material(deps: GraphDeps) -> Node:
    @node_timeout()
    async def material(state: QuizState) -> QuizState:
        """The quiz module and its lesson (port)."""
        assert state["quiz_id"] is not None  # guaranteed by `QuizInput`
        found = await deps.ports.quiz.material(deps.user_id, state["quiz_id"])
        return {"material": asdict(found)}

    return material


def make_save_quiz(deps: GraphDeps) -> Node:
    @node_timeout()
    async def save_quiz(state: QuizState) -> QuizState:
        """Questions and cards filed (idempotent per quiz), then announced."""
        material = material_of(state)
        assert state["draft"] is not None  # guaranteed by `route_write`
        draft = QuizDraft.model_validate(state["draft"])
        count = await deps.ports.quiz.save_quiz(
            deps.user_id, deps.session_id, material.quiz_id, draft
        )
        logger.info(
            "Quiz filed: session %s, quiz %s, %d question(s)",
            deps.session_id,
            material.quiz_id,
            count,
        )
        cards = len(draft.flashcards)
        text = f"Quiz ready with {count} questions and {cards} review cards."
        emit("agent.message", {"message_id": f"{AGENT}-quiz", "text": text}, agent=AGENT)
        artifact = {
            "artifact_id": material.quiz_id,
            "kind": "quiz",
            "title": draft.title,
            "url": f"/study/quiz/{material.quiz_id}",
        }
        emit("artifact.ready", artifact, agent=AGENT)
        return {"questions": count, "summary": f"Quiz ready for “{material.module_title}”."}

    return save_quiz


def make_failed(deps: GraphDeps) -> Node:
    @node_timeout()
    async def failed(state: QuizState) -> QuizState:
        """Failed quiz, with its reason (idempotent). The reason only quotes question numbers
        and counts, never the content written by the model."""
        material = material_of(state)
        reason = state["failure"]
        await deps.ports.quiz.quiz_failed(deps.user_id, material.quiz_id, reason)
        logger.info("Quiz failed: session %s, quiz %s", deps.session_id, material.quiz_id)
        text = f"Quiz generation failed. {reason}"
        emit("agent.message", {"message_id": f"{AGENT}-echec", "text": text}, agent=AGENT)
        return {"summary": f"Quiz generation failed for “{material.module_title}”."}

    return failed


def make_load_attempt(deps: GraphDeps) -> Node:
    @node_timeout()
    async def load_attempt(state: QuizState) -> QuizState:
        """The attempt to grade: open questions and answers, MCQ points, lesson (port)."""
        assert state["attempt_id"] is not None  # guaranteed by `QuizInput`
        found = await deps.ports.quiz.attempt(deps.user_id, state["attempt_id"])
        return {"attempt": asdict(found)}

    return load_attempt


def make_save_grades(deps: GraphDeps) -> Node:
    @node_timeout(SAVE_TIMEOUT_S)
    async def save_grades(state: QuizState) -> QuizState:
        """Grades filed by the port (idempotent per attempt: replayed, it rereads the grade)."""
        attempt_id = attempt_of(state).attempt_id
        grades = {ref: (float(p), str(text)) for ref, (p, text) in state["grades"].items()}
        saved = await deps.ports.quiz.save_grades(deps.user_id, deps.session_id, attempt_id, grades)
        logger.info(
            "Attempt graded: session %s, attempt %s, %d %%",
            deps.session_id,
            attempt_id,
            saved.score,
        )
        return {"graded": asdict(saved)}

    return save_grades


def graded_text(saved: GradedSaved) -> str:
    """What January reads at the end of the grading."""
    if saved.passed:
        text = f"You scored {saved.score}% and validated the skills."
    else:
        text = (
            f"You scored {saved.score}%. Passing requires {PASS_PERCENT}%. "
            f"Added {saved.followup_tasks} tasks to your program, including a retry in 2 days."
        )
    if saved.cards_created:
        count = saved.cards_created
        cards = "review card" if count == 1 else "review cards"
        text += f" Created {count} {cards} from your mistakes."
    return text


def make_announce(deps: GraphDeps) -> Node:
    @node_timeout()
    async def announce(state: QuizState) -> QuizState:
        """The announced grade (the per-question detail is read on the quiz page)."""
        attempt = attempt_of(state)
        saved = GradedSaved(**state["graded"])
        message = {"message_id": f"{AGENT}-note", "text": graded_text(saved)}
        emit("agent.message", message, agent=AGENT)
        return {"summary": f"Graded the quiz on “{attempt.module_title}” at {saved.score}%."}

    return announce
