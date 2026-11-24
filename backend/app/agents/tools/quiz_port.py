"""Port des quiz (D100). `app.agents` n'importe aucune feature (contrat 6) : il décrit ici ce dont
le parcours `quiz` a besoin (le module et sa leçon, le rangement du quiz, son échec, la tentative à
noter, le rangement des notes) ; la feature `quiz` l'implémentera (tâche 5.4).

Chaque écriture est idempotente (clé : le quiz, la tentative) : un nœud rejoué après un arrêt
(SPEC 9.4) rend la même chose, jamais une question, une fiche ni une note de plus.

Texte libre lu par January (réponse attendue, grille, explication, retour) : `Prose`, raccourci
plutôt que refusé (D97 n° 10). Énoncés, choix de QCM, code, compétences et références restent
refusés puis redemandés : couper l'un d'eux le rendrait faux.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Annotated, Protocol

from pydantic import AfterValidator, BaseModel, BeforeValidator, Field, WithJsonSchema

from app.agents.runtime.prose import Prose, ShortenToMax
from app.agents.tools.study_schema import CardDraft
from app.core.errors import AppError
from app.db.models.study import QuestionType

MIN_TYPES = 3  # au moins 3 types sur 4 : un module sans code n'a pas de lecture de code
# Bornes du quiz, lues aussi par l'écriture directe (`features/quiz`) : un quiz écrit à la main ne
# s'ouvre aux tentatives (donc aux acquis) qu'à ces bornes.
MIN_QUESTIONS = 8
MAX_QUESTIONS = 12
MIN_PROMPT_CHARS = 10
MIN_CHOICES = 3
MAX_CHOICES = 5
OPEN_SCORES = (0.0, 0.5, 1.0)  # notes d'une réponse ouverte

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
    """Problèmes d'une question, sans recopier son contenu (rendus au modèle, journalisés)."""
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
    """Le module dont on écrit le quiz, et sa leçon publiée."""

    quiz_id: str
    module_title: str
    skills: list[str]
    lesson_markdown: str
    language: str  # langue des leçons (`lesson_language` des réglages)


@dataclass(frozen=True)
class GradingItem:
    """Une question ouverte à noter, avec la réponse de January (contenu non fiable)."""

    ref: str  # « q3 » : rang de la question dans le quiz
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
    open_items: list[GradingItem]  # questions ouvertes seulement : un QCM n'est jamais envoyé
    qcm_points: dict[str, float]  # ref → 0 ou 1, notés par le code
    lesson_markdown: str  # la leçon du module (F12) : noter « explique avec tes mots » sur le sens


def _on_scale(score: float) -> float:
    if score not in OPEN_SCORES:
        raise ValueError("The score must be exactly 0, 0.5, or 1.")
    return score


# `Literal[0, 0.5, 1]` au schéma JSON, mais un nombre pour mypy (un `Literal` n'admet pas 0.5).
Score = Annotated[float, AfterValidator(_on_scale), WithJsonSchema({"enum": [0, 0.5, 1]})]


class GradeDraft(BaseModel):
    ref: str = Field(pattern=r"^q\d{1,2}$")
    score: Score  # hors de {0 ; 0,5 ; 1} : refusée, redemandée
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
        """Le module du quiz et sa leçon ; `quiz_not_found` (404) s'il n'est pas à lui."""
        ...

    async def save_quiz(self, user_id: str, session_id: str, quiz_id: str, draft: QuizDraft) -> int:
        """Range questions et fiches et rend le nombre de questions. Idempotent : un quiz déjà
        `ready` rend son nombre de questions sans rien écrire. Une compétence hors du module est
        rattachée à la première du module."""
        ...

    async def quiz_failed(self, user_id: str, quiz_id: str, reason: str) -> None:
        """Marque le quiz en échec avec une raison lisible ; idempotent."""
        ...

    async def attempt(self, user_id: str, attempt_id: str) -> AttemptToGrade:
        """La tentative à noter ; `attempt_not_found` (404) si elle n'est pas à lui."""
        ...

    async def save_grades(
        self,
        user_id: str,
        session_id: str,
        attempt_id: str,
        grades: Mapping[str, tuple[float, str]],
    ) -> GradedSaved:
        """Range les notes de toutes les questions, ref → (note, retour) : QCM par le code
        (retour vide, l'explication de la question suffit), ouvertes par l'Examinateur.
        Idempotent par tentative : une tentative déjà notée rend sa note sans rien écrire."""
        ...


def quiz_unavailable() -> AppError:
    return AppError("quiz_unavailable", "Les quiz ne sont pas branchés sur ce moteur.", 503)


class _NoQuiz:
    """Valeur par défaut du moteur (tests existants, démarrages sans la feature `quiz`)."""

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
