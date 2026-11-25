"""The Tutor (SPEC F14, 9.1, D102): structured outputs, January's answers to the questions, and
what its nodes share (context reading, prompts, messages).

Any free text from the model goes through `Prose` (shortened, never refused: D97 no. 10), except
the question, refused then requested again beyond 500 characters. The Mermaid schema has no cap
in the schema: a refusal would make the step fail; too long or invalid, it is removed by the code
(`teach`), never a failure."""

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, field_validator

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.events import AgentMessagePayload
from app.agents.runtime.prose import Prose
from app.agents.runtime.speech import CitationEntry, extract_citations
from app.agents.runtime.structured import structured_call
from app.agents.state.study_session import StudySessionState
from app.agents.tools.study_port import LessonSection, StudyContext

AGENT = "tutor"
MAX_HINTS = 3
MAX_ANSWER_CHARS = 4000
LESSON_CHARS = 20_000  # a 2,500-word lesson fits entirely
TUTOR_QUESTION = "tutor_question"
FINISH_SESSION = "finish_session"
LESSON_LABEL = "lesson"
ANSWER_LABEL = "January's answer"

TutorAction = Literal["answer", "stuck", "skip", "finish"]


class Node(Protocol):
    async def __call__(self, state: StudySessionState) -> StudySessionState: ...


class TeachTurn(BaseModel):
    message: Prose = Field(min_length=1, max_length=2500)
    question: str = Field(min_length=5, max_length=500)
    expected: Prose = Field(min_length=1, max_length=800)
    mermaid: str | None = None  # no cap here: too long or invalid, removed by the code


class AnswerCheck(BaseModel):
    verdict: Literal["correct", "partial", "wrong"]
    feedback: Prose = Field(min_length=1, max_length=1200)


class HintTurn(BaseModel):
    hint: Prose = Field(min_length=1, max_length=600)


class FinalQuestion(BaseModel):
    question: str = Field(min_length=5, max_length=500)
    expected: Prose = Field(min_length=1, max_length=800)


class FinalQuestions(BaseModel):
    """Exactly 3 questions; beyond that, the first 3 are kept without failure (m2 of the
    5.5 reread); fewer than 3 remains a refusal, requested again."""

    questions: list[FinalQuestion] = Field(min_length=3, max_length=3)

    @field_validator("questions", mode="before")
    @classmethod
    def _first_three(cls, value: Any) -> Any:
        return value[:3] if isinstance(value, list) else value


class SessionSummary(BaseModel):
    summary: Prose = Field(min_length=1, max_length=700)


class TutorReply(BaseModel):
    """Answer to a January question (at the opening, or by message during the session)."""

    message: Prose = Field(min_length=1, max_length=1500)


@dataclass(frozen=True)
class TutorAnswer:
    action: TutorAction
    text: str = ""


_ACTIONS: dict[Any, TutorAction] = {"stuck": "stuck", "skip": "skip", "finish": "finish"}


def parse_tutor_answer(value: Any) -> TutorAnswer | None:
    """`{"answers": {"answer": text}}` (non-empty text, cut at 4,000) -> `answer`; `"stuck"`,
    `"skip"`, `"finish"` (value of an option); `{"action": "finish"}` ("Finish", 5.6) ->
    `finish`. Any other shape: `None` (the question is asked again)."""
    if isinstance(value, str):
        action = _ACTIONS.get(value)
        return TutorAnswer(action) if action is not None else None
    if not isinstance(value, dict):
        return None
    if value.get("action") == "finish":
        return TutorAnswer("finish")
    answers = value.get("answers")
    text = answers.get("answer") if isinstance(answers, dict) else None
    if isinstance(text, str) and text.strip():
        return TutorAnswer("answer", text.strip()[:MAX_ANSWER_CHARS])
    return None


def context_of(state: StudySessionState) -> StudyContext:
    data = dict(state["context"])
    sections = [LessonSection(**s) for s in data.pop("sections")]
    sources = [CitationEntry(**s) for s in data.pop("sources")]
    return StudyContext(sections=sections, sources=sources, **data)


def section_text(section: LessonSection) -> str:
    return f"## {section.title}\n\n{section.markdown}"


def lesson_prompt(text: str) -> str:
    """Lesson (written by the Writer from the web): untrusted content, wrapped."""
    return untrusted(text[:LESSON_CHARS], LESSON_LABEL)


def whole_lesson(context: StudyContext) -> str:
    parts = [section_text(s) for s in context.sections]
    parts.append(f"## Exercise\n\n{context.exercise}")
    return lesson_prompt("\n\n".join(parts))


def _sources_prompt(sources: list[CitationEntry]) -> str:
    if not sources:
        return "No sources are available to cite. Omit bracketed numbers."
    return "\n".join(
        f"[{s.index}] " + untrusted(" ".join(s.title.split()), f"source {s.index}") for s in sources
    )


def _module_prompt(context: StudyContext) -> str:
    """Title and objectives come from the program and the lesson (agent outputs): wrapped."""
    lines = [f"Title: {context.module_title}", "Objectives"]
    lines += [f"- {objective}" for objective in context.objectives] or ["- None specified"]
    return untrusted("\n".join(lines), "module")


def tutor_prompt(
    state: StudySessionState, task: str, *, memory: bool = False, **variables: object
) -> str:
    """The Tutor's prompt for `task`: module, sources and study mode always; the memory context
    (already wrapped by the port) when `memory`."""
    context = context_of(state)
    return render_prompt(
        AGENT,
        task=task,
        study_mode=context.mode,
        module=_module_prompt(context),
        sources=_sources_prompt(context.sources),
        memory=state.get("memory", "") if memory else "",
        **variables,
    )


async def ask_tutor[T: BaseModel](
    deps: GraphDeps, schema: type[T], prompt: str, request: str, *, step: str, intent: str
) -> T:
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    return await structured_call(
        model,
        schema,
        [SystemMessage(prompt), HumanMessage(request)],
        agent=AGENT,
        step=step,
        intent=intent,
    )


def say(state: StudySessionState, text: str, message_id: str) -> None:
    """The Tutor's `agent.message`, with the `[n]` citations of the lesson's sources. A fixed id
    per step: replayed, the message replaces the previous one instead of adding to it (D57)."""
    sources = context_of(state).sources
    payload = AgentMessagePayload(
        message_id=message_id, text=text, citations=extract_citations(text, sources)
    )
    emit("agent.message", payload, agent=AGENT)


def notes_prompt(notes: list[str]) -> str:
    """January's messages (not wrapped, D53 section 5), one line each."""
    return "\n".join(f"- {' '.join(note.split())}" for note in notes)


def outcome_record(
    state: StudySessionState, verdict: str, *, checked: bool = True
) -> list[dict[str, Any]]:
    """`outcomes` completed with the fate of the current question. `checked=False`: January
    answered but the model could not judge (fallback, `skipped`); marked in the state only
    (`unchecked`), never in `StudyOutcome` (D115 no. 17)."""
    record: dict[str, Any] = {
        "phase": state["phase"],
        "index": state.get("index", 0),
        "question": state["question"],
        "expected": state["expected"],
        "verdict": verdict,
        "hints": state.get("hints", 0),
    }
    if not checked:
        record["unchecked"] = True
    return [*state.get("outcomes", []), record]


_VERDICTS = {
    "correct": "correct",
    "partial": "partly correct",
    "wrong": "incorrect",
    "skipped": "skipped",
    "revealed": "solution shown",
}
UNCHECKED_LABEL = "answered, unchecked (the model did not respond)"


def _verdict_label(outcome: dict[str, Any]) -> str:
    return UNCHECKED_LABEL if outcome.get("unchecked") else _VERDICTS[outcome["verdict"]]


def outcomes_prompt(state: StudySessionState) -> str:
    """The questions already settled and their fate. The questions come from the Tutor, written
    from an untrusted lesson: wrapped."""
    outcomes = state.get("outcomes", [])
    if not outcomes:
        return "No questions resolved yet."
    lines = [
        f"- {' '.join(o['question'].split())[:300]}: {_verdict_label(o)}, {o['hints']} hint(s)"
        for o in outcomes
    ]
    return untrusted("\n".join(lines), "session")
