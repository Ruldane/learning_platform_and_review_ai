"""Port for quizzes (D100). `app.agents` imports no feature (contract 6): it describes here what
the `quiz` graph needs (the module and its lesson, storing the quiz, its failure, the attempt to
grade, storing the grades); the `quiz` feature will implement it (task 5.4).

Each write is idempotent (key: the quiz, the attempt): a node replayed after a stop
(SPEC 9.4) returns the same thing, never one more question, card or grade.

Free text read from January (expected answer, grid, explanation, feedback): `Prose`, shortened
rather than refused (D97 no. 10). Statements, multiple-choice options, code, skills and references
stay refused and are asked again: cutting one of them would make it false.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Annotated, Protocol

from pydantic import AfterValidator, BaseModel, BeforeValidator, Field, WithJsonSchema

from app.agents.runtime.prose import Prose, ShortenToMax
from app.agents.tools.study_schema import CardDraft
from app.core.errors import AppError
from app.db.models.study import QuestionType

MIN_TYPES = 3  # at least 3 types out of 4: a module without code has no code reading
# Quiz bounds, also read by direct writing (`features/quiz`): a quiz written by hand only opens
# to attempts (so to acquired skills) within these bounds.
MIN_QUESTIONS = 8
MAX_QUESTIONS = 12
MIN_PROMPT_CHARS = 10
MIN_CHOICES = 3
MAX_CHOICES = 5
OPEN_SCORES = (0.0, 0.5, 1.0)  # scores of an open answer

Choice = Annotated[str, Field(min_length=1, max_length=200)]
Criterion = Annotated[str, Field(min_length=1, max_length=200), ShortenToMax()]


def read_question_type(value: object) -> object:
    """Read question types from checkpoints saved before migration 0080."""
    return "mcq" if value == "qcm" else value


class QuestionDraft(BaseModel):
    type: Annotated[QuestionType, BeforeValidator(read_question_type)]
    prompt: str = Field(min_length=MIN_PROMPT_CHARS, max_length=600)
    code: str | None = Field(default=None, max_length=3000)
    choices: list[Choice] = Field(default_factory=list, max_length=MAX_CHOICES)
    correct_index: int | None = None
    expected: Prose = Field(min_length=1, max_length=800)
    rubric: list[Criterion] = Field(min_length=1, max_length=4)
    explanation: Prose = Field(min_length=1, max_length=800)
    skill: str = Field(min_length=2, max_length=120)


class QuizDraft(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    questions: list[QuestionDraft] = Field(min_length=MIN_QUESTIONS, max_length=MAX_QUESTIONS)
    flashcards: list[CardDraft] = Field(min_length=3, max_length=6)


def _question_problems(number: int, question: QuestionDraft) -> list[str]:
    """Problems of a question, without copying its content (returned to the model, logged)."""
    where = f"Question {number} ({question.type})"
    if question.type == "mcq":
        distinct = {" ".join(c.casefold().split()) for c in question.choices}
        problems = []
        if not MIN_CHOICES <= len(question.choices) <= MAX_CHOICES:
            problems.append(f"{where}: give 3 to 5 choices, currently {len(question.choices)}.")
        elif len(distinct) != len(question.choices):
            problems.append(f"{where}: all choices must be distinct.")
        index = question.correct_index
        if index is None or not 0 <= index < len(question.choices):
            problems.append(
                f"{where}: `correct_index` must select a choice "
                f"(0 to {max(len(question.choices) - 1, 0)})."
            )
        return problems
    problems = []
    if question.type == "code" and not (question.code or "").strip():
        problems.append(f"{where}: put the snippet for a code reading question in `code`.")
    if question.choices or question.correct_index is not None:
        problems.append(
            f"{where}: only multiple-choice questions have choices and a correct index."
        )
    return problems


def quiz_problems(draft: QuizDraft) -> list[str]:
    """Validate question shapes and variety without repeating the content in error messages."""
    problems: list[str] = []
    types = {q.type for q in draft.questions}
    if len(types) < MIN_TYPES:
        problems.append(
            f"Use at least 3 of the question types mcq, short, code and explain "
            f"(currently {len(types)})."
        )
    for number, question in enumerate(draft.questions, start=1):
        problems += _question_problems(number, question)
    return problems


@dataclass(frozen=True)
class ModuleMaterial:
    """The module whose quiz is written, and its published lesson."""

    quiz_id: str
    module_title: str
    skills: list[str]
    lesson_markdown: str
    language: str  # lesson language (`lesson_language` setting)


@dataclass(frozen=True)
class GradingItem:
    """An open question to grade, with January's answer (untrusted content)."""

    ref: str  # "q3": rank of the question in the quiz
    type: QuestionType
    prompt: str
    code: str | None
    expected: str
    rubric: list[str]
    answer: str


@dataclass(frozen=True)
class AttemptToGrade:
    attempt_id: str
    module_title: str
    open_items: list[GradingItem]  # open questions only: a multiple choice is never sent
    qcm_points: dict[str, float]  # ref -> 0 or 1, graded by the code
    lesson_markdown: str  # the module's lesson (F12): grade "explain in your own words" on meaning


def _on_scale(score: float) -> float:
    if score not in OPEN_SCORES:
        raise ValueError("The score must be exactly 0, 0.5, or 1.")
    return score


# `Literal[0, 0.5, 1]` in the JSON schema, but a number for mypy (a `Literal` does not accept 0.5).
Score = Annotated[float, AfterValidator(_on_scale), WithJsonSchema({"enum": [0, 0.5, 1]})]


class GradeDraft(BaseModel):
    ref: str = Field(pattern=r"^q\d{1,2}$")
    score: Score  # outside {0; 0.5; 1}: refused, asked again
    feedback: Prose = Field(min_length=1, max_length=600)


class Grades(BaseModel):
    items: list[GradeDraft] = Field(min_length=1, max_length=12)


@dataclass(frozen=True)
class GradedSaved:
    attempt_id: str
    score: int  # pourcentage
    passed: bool
    cards_created: int
    followup_tasks: int


class QuizStore(Protocol):
    async def material(self, user_id: str, quiz_id: str) -> ModuleMaterial:
        """The quiz's module and its lesson; `quiz_not_found` (404) if it is not theirs."""
        ...

    async def save_quiz(self, user_id: str, session_id: str, quiz_id: str, draft: QuizDraft) -> int:
        """Stores questions and cards; returns the number of questions. Idempotent: a quiz already
        `ready` returns its number of questions without writing anything. A skill outside the module
        is attached to the module's first one."""
        ...

    async def quiz_failed(self, user_id: str, quiz_id: str, reason: str) -> None:
        """Marks the quiz as failed with a readable reason; idempotent."""
        ...

    async def attempt(self, user_id: str, attempt_id: str) -> AttemptToGrade:
        """The attempt to grade; `attempt_not_found` (404) if it is not theirs."""
        ...

    async def save_grades(
        self,
        user_id: str,
        session_id: str,
        attempt_id: str,
        grades: Mapping[str, tuple[float, str]],
    ) -> GradedSaved:
        """Stores the grades of all questions, ref -> (grade, feedback): multiple choice by the code
        (empty feedback, the question's explanation is enough), open ones by the Examiner.
        Idempotent per attempt: an already graded attempt returns its grade, writing nothing."""
        ...


def quiz_unavailable() -> AppError:
    return AppError("quiz_unavailable", "Quizzes are unavailable in this runtime.", 503)


class _NoQuiz:
    """Engine default value (existing tests, starts without the `quiz` feature)."""

    async def material(self, user_id: str, quiz_id: str) -> ModuleMaterial:
        raise quiz_unavailable()

    async def save_quiz(self, user_id: str, session_id: str, quiz_id: str, draft: QuizDraft) -> int:
        raise quiz_unavailable()

    async def quiz_failed(self, user_id: str, quiz_id: str, reason: str) -> None:
        raise quiz_unavailable()

    async def attempt(self, user_id: str, attempt_id: str) -> AttemptToGrade:
        raise quiz_unavailable()

    async def save_grades(
        self,
        user_id: str,
        session_id: str,
        attempt_id: str,
        grades: Mapping[str, tuple[float, str]],
    ) -> GradedSaved:
        raise quiz_unavailable()


NO_QUIZ: QuizStore = _NoQuiz()
