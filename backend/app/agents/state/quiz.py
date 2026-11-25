"""State of the `quiz` graph (D100). The quiz and notes are in the database (port `QuizStore`):
the state only keeps what passes from one node to the next (the module, the Examiner's draft, the
attempt, the notes to store) and what must be announced."""

from typing import Any, TypedDict


class QuizState(TypedDict, total=False):
    mode: str  # `generate`: write the quiz; `grade`: grade an attempt
    quiz_id: str | None
    attempt_id: str | None
    material: dict[str, Any]  # `ModuleMaterial` as JSON
    draft: dict[str, Any] | None  # `QuizDraft` as JSON; None: quiz invalid after 3 tries
    failure: str  # reason the quiz failed
    questions: int  # questions stored
    attempt: dict[str, Any]  # `AttemptToGrade` as JSON
    grades: dict[str, list[Any]]  # ref -> [grade, feedback], all questions of the attempt
    graded: dict[str, Any]  # `GradedSaved` as JSON
    summary: str
