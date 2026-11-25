"""The Examiner (SPEC 9.1, F9, D100) writes a module's quiz and grades the open answers of an
attempt.

`write` asks for a `QuizDraft` and has it checked by `quiz_problems`: the problems go back to the
model, twice at most (`MAX_QUIZ_ASKS` = one request and two re-requests); after that the quiz is
declared invalid (`failure`) and the flow files it as failed.

`grade_open` makes a single request for all the open answers (none: no call). Each answer is
wrapped as untrusted (`untrusted`, SPEC 17.4), the lesson too; the multiple-choice questions,
graded by the code, are never sent to the model. An unknown reference is ignored; if some
questions remain ungraded (forgotten or renumbered), a single new request names them (final
review of phase 5, A-I1); after that, an ungraded question is worth 0 with `MISSING_FEEDBACK`.
A grade outside {0; 0.5; 1} is refused by the schema and requested again.

None of these nodes touches a port: replayed, they ask the model again without writing anything."""

import logging
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.agents.nodes.examiner_flow import AGENT, Node, attempt_of, material_of
from app.agents.nodes.lesson_common import LANGUAGES
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.quiz import QuizState
from app.agents.tools.quiz_port import (
    GradeDraft,
    Grades,
    GradingItem,
    ModuleMaterial,
    QuizDraft,
    quiz_problems,
)

MAX_QUIZ_ASKS = 3  # one request + two re-requests with the problems from `quiz_problems`
MAX_GRADE_ASKS = 2  # one request + one re-request if some questions remain ungraded
MISSING_FEEDBACK = "This answer wasn't graded. Review the explanation."
WRITE_REQUEST = "Write the module quiz."
GRADE_REQUEST = "Grade the free-text answers."
LESSON_CHARS = 20_000  # a 2,500-word lesson fits entirely
MAX_REASON_CHARS = 300  # `quizzes.failure_reason`
WRITE_TIMEOUT_S = 600  # three requests of a full quiz, with their retries
GRADE_TIMEOUT_S = 300

logger = logging.getLogger(__name__)


def _module_prompt(material: ModuleMaterial) -> str:
    """Title and skills come from the program (agent output): wrapped data."""
    lines = [
        f"Title: {material.module_title}",
        f"Skills: {', '.join(material.skills) or 'none specified'}",
    ]
    return untrusted("\n".join(lines), "module")


def _lesson(markdown: str) -> str:
    return untrusted(markdown[:LESSON_CHARS], "lesson")


def _problems_text(problems: list[str]) -> str:
    return (
        "Your quiz does not follow the rules:\n"
        + "\n".join(f"- {problem}" for problem in problems)
        + "\nFix it and return the complete quiz again."
    )


async def _ask_quiz(deps: GraphDeps, prompt: str) -> tuple[QuizDraft, list[str]]:
    """One request, then two re-requests at most; returns the last draft and its problems."""
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    messages: list[BaseMessage] = [SystemMessage(prompt), HumanMessage(WRITE_REQUEST)]
    found: QuizDraft | None = None
    problems: list[str] = []
    for ask in range(1, MAX_QUIZ_ASKS + 1):
        if found is not None:
            messages += [AIMessage(found.model_dump_json()), HumanMessage(_problems_text(problems))]
        found = await structured_call(
            model,
            QuizDraft,
            messages,
            agent=AGENT,
            step=f"quiz-{ask}",
            intent="writing the module quiz" if ask == 1 else "revising the quiz",
        )
        problems = quiz_problems(found)
        if not problems:
            break
    assert found is not None
    return found, problems


def make_write(deps: GraphDeps) -> Node:
    @node_timeout(WRITE_TIMEOUT_S)
    async def write(state: QuizState) -> QuizState:
        material = material_of(state)
        prompt = render_prompt(
            AGENT,
            mode="write",
            module=_module_prompt(material),
            lesson=_lesson(material.lesson_markdown),
            language=LANGUAGES.get(material.language, material.language),
            min_questions=8,
            max_questions=12,
            min_cards=3,
            max_cards=6,
        )
        draft, problems = await _ask_quiz(deps, prompt)
        if not problems:
            return {"draft": draft.model_dump(mode="json")}
        logger.info(
            "Invalid quiz: session %s, quiz %s, %d problem(s) after %d attempts",
            deps.session_id,
            material.quiz_id,
            len(problems),
            MAX_QUIZ_ASKS,
        )
        reason = f"Quiz still invalid after {MAX_QUIZ_ASKS} attempts. " + ". ".join(problems)
        return {"draft": None, "failure": reason[:MAX_REASON_CHARS]}

    return write


def route_write(state: QuizState) -> str:
    return "save_quiz" if state.get("draft") else "failed"


def _item_prompt(item: GradingItem) -> str:
    """One question (data written by the Examiner from an untrusted lesson) and January's
    answer, each in its own wrapper."""
    lines = [f"Prompt: {item.prompt}"]
    if item.code:
        lines.append(f"Code :\n{item.code}")
    lines.append(f"Expected answer: {item.expected}")
    lines.append("Rubric:\n" + "\n".join(f"- {criterion}" for criterion in item.rubric))
    return (
        f"### {item.ref} ({item.type})\n"
        + untrusted("\n".join(lines), f"question {item.ref}")
        + f"\nJanuary's answer to {item.ref}:\n"
        + untrusted(item.answer, "January's answer")
    )


def _grades_by_ref(
    found: list[GradeDraft], items: list[GradingItem]
) -> tuple[dict[str, list[Any]], list[str]]:
    """Grade of each open question (the first one given for a reference); ungraded: 0 and
    `MISSING_FEEDBACK`. Also returns the references left ungraded, in quiz order."""
    refs = {item.ref for item in items}
    given: dict[str, GradeDraft] = {}
    for draft in found:
        if draft.ref in refs:
            given.setdefault(draft.ref, draft)
    grades: dict[str, list[Any]] = {}
    for item in items:
        grade = given.get(item.ref)
        grades[item.ref] = [grade.score, grade.feedback] if grade else [0.0, MISSING_FEEDBACK]
    return grades, [item.ref for item in items if item.ref not in given]


def _missing_text(missing: list[str]) -> str:
    return (
        "Your grading forgets these questions: "
        + ", ".join(missing)
        + ". Reuse exactly the reference of each question (the one in its heading "
        '"### qN") and return the complete grading of all the questions.'
    )


async def _ask_grades(
    deps: GraphDeps, prompt: str, items: list[GradingItem]
) -> tuple[list[GradeDraft], list[str]]:
    """One request; if some questions remain ungraded, a single new request that names them.
    Returns all the grades received (the first for a reference wins) and the ungraded
    references."""
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    messages: list[BaseMessage] = [SystemMessage(prompt), HumanMessage(GRADE_REQUEST)]
    received: list[GradeDraft] = []
    missing: list[str] = []
    for ask in range(1, MAX_GRADE_ASKS + 1):
        found = await structured_call(
            model,
            Grades,
            messages,
            agent=AGENT,
            step=f"notation-{ask}",
            intent="grading your free-text answers" if ask == 1 else "completing the grading",
        )
        received += found.items
        missing = _grades_by_ref(received, items)[1]
        if not missing:
            break
        messages += [AIMessage(found.model_dump_json()), HumanMessage(_missing_text(missing))]
    return received, missing


def make_grade_open(deps: GraphDeps) -> Node:
    @node_timeout(GRADE_TIMEOUT_S)
    async def grade_open(state: QuizState) -> QuizState:
        attempt = attempt_of(state)
        grades: dict[str, list[Any]] = {ref: [p, ""] for ref, p in attempt.qcm_points.items()}
        # Multiple-choice questions are scored locally even if the port passes one here.
        items = [item for item in attempt.open_items if item.type != "mcq"]
        if not items:
            return {"grades": grades}
        prompt = render_prompt(
            AGENT,
            mode="grade",
            module=untrusted(f"Title: {attempt.module_title}", "module"),
            lesson=_lesson(attempt.lesson_markdown),
            items="\n\n".join(_item_prompt(item) for item in items),
        )
        received, missing = await _ask_grades(deps, prompt, items)
        open_grades, _ = _grades_by_ref(received, items)
        unknown = sum(1 for grade in received if grade.ref not in open_grades)
        logger.info(
            "Answers graded: session %s, attempt %s, %d open, %d ungraded, %d unknown reference(s)",
            deps.session_id,
            attempt.attempt_id,
            len(items),
            len(missing),
            unknown,
        )
        return {"grades": grades | open_grades}

    return grade_open
