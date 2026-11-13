"""Port des sessions d'étude guidées (SPEC F14, D102). `app.agents` n'importe aucune feature
(contrat 6) : il décrit ici ce dont le parcours `study_session` a besoin (la leçon découpée en
sections, l'exercice et son corrigé, les sources ; le rangement de la fin de session) ; la feature
`study` l'implémentera (tâche 5.6).

Le parcours ne lit qu'une fois (`context`) et n'écrit qu'une fois (`finish`), à la fin ;
`finish` est idempotent : une session d'étude déjà `finished` est relue telle quelle, sans
seconde écriture (nœud rejoué après un arrêt, SPEC 9.4).
"""

from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.agents.runtime.speech import CitationEntry
from app.core.errors import AppError
from app.db.models.skills import SkillLevel
from app.db.models.study import StudyMode

Verdict = Literal["correct", "partial", "wrong", "skipped", "revealed"]
OutcomePhase = Literal["section", "exercise", "final"]
PRACTICE_VERDICTS: tuple[Verdict, ...] = ("correct", "partial")  # l'exercice est fait (F13)


@dataclass(frozen=True)
class LessonSection:
    title: str
    markdown: str


@dataclass(frozen=True)
class StudyContext:
    """Ce que le Tuteur connaît de la séance : la leçon du module (sections enseignées présentes
    parmi L'essentiel, Explication, Schémas, Exemple travaillé, Erreurs fréquentes, dans cet
    ordre), son exercice et son corrigé, ses sources numérotées, et la question que January a
    posée en ouvrant la session (`None` : aucune)."""

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
    """Le sort d'une question : `index` = rang de la section (0…), 0 pour l'exercice, rang de la
    question finale (0…2) ; `hints` = indices donnés avant le verdict."""

    phase: OutcomePhase
    index: int
    question: str
    expected: str
    verdict: Verdict
    hints: int


@dataclass(frozen=True)
class StudyOutcome:
    """Ce que la session a produit. `exercise_done` : l'exercice a reçu un verdict `correct` ou
    `partial` (F13). `ended_early` : January a terminé avant la dernière question."""

    outcomes: list[Outcome]
    exercise_done: bool
    ended_early: bool
    summary: str


@dataclass(frozen=True)
class StudyFinished:
    """Ce que la feature a rangé : minutes comptées, tâches cochées (titres), fiches créées depuis
    les erreurs, acquis dont le niveau a changé."""

    minutes: int
    tasks_done: list[str]
    flashcards_created: int
    skills: list[tuple[str, SkillLevel]]


class StudyStore(Protocol):
    async def context(self, user_id: str, study_session_id: str) -> StudyContext: ...

    async def finish(
        self, user_id: str, session_id: str, study_session_id: str, outcome: StudyOutcome
    ) -> StudyFinished:
        """Idempotent : une session d'étude déjà `finished` est relue, rien n'est réécrit."""
        ...


def exercise_done(outcomes: list[Outcome]) -> bool:
    """L'exercice est fait s'il a reçu `correct` ou `partial` ; `revealed` et `skipped` ne
    cochent pas la pratique (F13)."""
    return any(o.phase == "exercise" and o.verdict in PRACTICE_VERDICTS for o in outcomes)


def study_unavailable() -> AppError:
    return AppError(
        "study_unavailable", "Les sessions d'étude ne sont pas branchées sur ce moteur.", 503
    )


class _NoStudy:
    """Valeur par défaut du moteur (tests existants, démarrages sans la feature `study`)."""

    async def context(self, user_id: str, study_session_id: str) -> StudyContext:
        raise study_unavailable()

    async def finish(
        self, user_id: str, session_id: str, study_session_id: str, outcome: StudyOutcome
    ) -> StudyFinished:
        raise study_unavailable()


NO_STUDY: StudyStore = _NoStudy()
