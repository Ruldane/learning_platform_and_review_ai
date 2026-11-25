"""Port of the guided study sessions (SPEC F14, D102). `app.agents` imports no feature
(contract 6): it describes here what the `study_session` graph needs (the lesson split into
sections, the exercise and its model answer, the sources; the storing of the end of session); the
`study` feature implements it (task 5.6, D103).

The graph reads only once (`context`) and writes only once (`finish`), at the end;
`finish` is idempotent: a study session already `finished` is reread as is, without a
second write (node replayed after a stop, SPEC 9.4).
"""

from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.agents.runtime.speech import CitationEntry
from app.core.errors import AppError
from app.db.models.skills import SkillLevel
from app.db.models.study import StudyMode

Verdict = Literal["correct", "partial", "wrong", "skipped", "revealed"]
OutcomePhase = Literal["section", "exercise", "final"]
PRACTICE_VERDICTS: tuple[Verdict, ...] = ("correct", "partial")  # the exercise is done (F13)


@dataclass(frozen=True)
class LessonSection:
    title: str
    markdown: str


@dataclass(frozen=True)
class StudyContext:
    """What the Tutor knows of the session: the module's lesson (taught sections present among
    the section titles "L'essentiel", "Explication", "Schémas", "Exemple travaillé",
    "Erreurs fréquentes", in that order), its exercise and model answer, numbered sources,
    and the question January asked when opening the session (`None`: none)."""

    study_session_id: str
    module_title: str
    mode: StudyMode
    objectives: list[str]
    sections: list[LessonSection]
    exercise: str
    solution: str
    sources: list[CitationEntry] = field(default_factory=list)
    question: str | None = None


@dataclass(frozen=True)
class Outcome:
    """The outcome of a question: `index` = section rank (0...), 0 for the exercise, final
    question rank (0...2); `hints` = hints given before the verdict."""

    phase: OutcomePhase
    index: int
    question: str
    expected: str
    verdict: Verdict
    hints: int


@dataclass(frozen=True)
class StudyOutcome:
    """What the session produced. `exercise_done`: the exercise received a `correct` or
    `partial` verdict (F13). `ended_early`: January finished before the last question."""

    outcomes: list[Outcome]
    exercise_done: bool
    ended_early: bool
    summary: str


@dataclass(frozen=True)
class StudyFinished:
    """What the feature stored: minutes counted, tasks ticked (titles), cards created from
    the mistakes, skills whose level changed."""

    minutes: int
    tasks_done: list[str]
    flashcards_created: int
    skills: list[tuple[str, SkillLevel]]


class StudyStore(Protocol):
    """Guarantees of the implementation (`study` feature, D103): another user's session raises an
    `AppError` 404 (`study_session_not_found`) in `context` as in
    `finish`; `context` never returns an exercise without a model answer (empty `solution`: exercise
    omitted), so never an empty "Show the solution"; `finish` raises no skill beyond
    `en_cours` (only a quiz or a project validates, 4.5)."""

    async def context(self, user_id: str, study_session_id: str) -> StudyContext: ...

    async def finish(
        self, user_id: str, session_id: str, study_session_id: str, outcome: StudyOutcome
    ) -> StudyFinished:
        """Idempotent: a study session already `finished` is reread, nothing is rewritten
        (time, tasks, cards, skills, journal); abandoned in the meantime: empty end."""
        ...


def exercise_done(outcomes: list[Outcome]) -> bool:
    """The exercise is done if it received `correct` or `partial`; `revealed` and `skipped` do not
    tick the practice (F13)."""
    return any(o.phase == "exercise" and o.verdict in PRACTICE_VERDICTS for o in outcomes)


def study_unavailable() -> AppError:
    return AppError("study_unavailable", "Study sessions are unavailable in this runtime.", 503)


class _NoStudy:
    """Engine default value (existing tests, starts without the `study` feature)."""

    async def context(self, user_id: str, study_session_id: str) -> StudyContext:
        raise study_unavailable()

    async def finish(
        self, user_id: str, session_id: str, study_session_id: str, outcome: StudyOutcome
    ) -> StudyFinished:
        raise study_unavailable()


NO_STUDY: StudyStore = _NoStudy()
