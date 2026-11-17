"""Port des projets preuves (P1 à P4, D165). `app.agents` n'importe aucune feature (contrat 6) : il
décrit ici ce dont les parcours `project_brief` et `project_review` ont besoin ; la feature
`projects` l'implémente (tâche 8.10).

L'énoncé, la description de January, le dépôt, les critères et les brouillons sont des données de
l'utilisatrice ou du web (17.2, 17.4) : jamais journalisés, ni ici ni par l'implémentation. Toute
écriture est **idempotente par session** (SPEC 9.4) : un nœud rejoué après un arrêt ne range rien de
plus (la première écriture de la session gagne).

- `brief_inputs` / `review_inputs` : lecture seule, l'état du projet tel qu'il est en base.
- `save_brief` : range l'énoncé ; le projet passe à « à faire ».
- `brief_failed` : l'énoncé a échoué avec ce code (`structured_output_invalid`…), rien d'autre ;
  « Réessayer » relance le parcours.
- `repo_text` : le texte d'**une** page du dépôt (README), `None` si elle ne se lit pas. Point
  d'accroche de la phase 14 (GitHub) ; le parcours ne lit jamais le web autrement.
- `save_review` : range l'évaluation. Validée, le port monte les compétences du module à `prouve`
  (preuve `project`), range les brouillons et écrit au journal ; l'entrée de projet n'entre au
  profil maître que par le clic de January (P3).
- `save_drafts` : range les brouillons d'un projet **déjà validé** qui n'en a pas (mode `drafts`
  de `project_review`, D181) ; sans effet si le projet n'est pas validé, s'il a déjà des
  brouillons ou si la liste est vide."""

from dataclasses import dataclass
from typing import Literal, Protocol

from app.agents.tools.cv_schema import MasterProfileData
from app.agents.tools.project_schema import (
    CriterionResult,
    DraftKind,
    DraftStatus,
    ProfileEntryDraft,
    ProjectBrief,
)
from app.core.errors import AppError

__all__ = [
    "NO_PROJECTS",
    "BriefInputs",
    "DraftResult",
    "ProjectStore",
    "ReviewInputs",
    "ReviewOutcome",
]

LESSON_EXCERPT_MAX = 3_000  # caractères de l'extrait de leçon montrés au Praticien


@dataclass(frozen=True)
class BriefInputs:
    """Ce que le Praticien lit pour écrire l'énoncé du module."""

    module_title: str
    skills: list[str]
    prerequisites: list[str]
    lesson_excerpt: str | None  # 3 000 caractères au plus
    week_deliverable: str | None  # le livrable de la semaine du module
    role: str | None  # le poste visé
    language: Literal["fr", "en"]


@dataclass(frozen=True)
class ReviewInputs:
    """Ce que le Praticien lit pour évaluer le rendu : l'énoncé et ce que January a rendu."""

    title: str
    brief: ProjectBrief
    repo_url: str | None
    description: str | None
    screenshots: int  # nombre de captures : jamais envoyées au modèle (P2)
    skills: list[str]  # les compétences du module
    profile: MasterProfileData | None  # le profil maître validé
    language: Literal["fr", "en"]


@dataclass(frozen=True)
class DraftResult:
    kind: DraftKind
    content: str  # le texte contrôlé (`draft_text`)
    entry: ProfileEntryDraft | None  # seulement pour `profile_entry`
    status: DraftStatus  # `to_check` : des termes que January n'a pas dits, ou une longueur
    flags: list[str]  # ces termes (ou la longueur), jamais vide si `to_check`


@dataclass(frozen=True)
class ReviewOutcome:
    verdict: Literal["validated", "to_redo"]
    results: list[CriterionResult]  # un par critère, dans l'ordre (`settled_results`)
    feedback: str
    repo_status: Literal["read", "unreadable", "none"]
    drafts: list[DraftResult] | None  # quatre brouillons si validé, sinon `None`


class ProjectStore(Protocol):
    async def brief_inputs(self, user_id: str, project_id: str) -> BriefInputs: ...

    async def save_brief(
        self, user_id: str, session_id: str, project_id: str, brief: ProjectBrief
    ) -> None: ...

    async def brief_failed(
        self, user_id: str, session_id: str, project_id: str, code: str
    ) -> None: ...

    async def review_inputs(self, user_id: str, project_id: str) -> ReviewInputs: ...

    async def repo_text(self, user_id: str, session_id: str, url: str) -> str | None: ...

    async def save_review(
        self, user_id: str, session_id: str, project_id: str, outcome: ReviewOutcome
    ) -> None: ...

    async def save_drafts(
        self, user_id: str, session_id: str, project_id: str, drafts: list[DraftResult]
    ) -> None: ...


def projects_unavailable() -> AppError:
    return AppError("projects_unavailable", "Les projets ne sont pas branchés sur ce moteur.", 503)


class _NoProjects:
    """Valeur par défaut du moteur (tests, démarrages sans la feature)."""

    async def brief_inputs(self, user_id: str, project_id: str) -> BriefInputs:
        raise projects_unavailable()

    async def save_brief(
        self, user_id: str, session_id: str, project_id: str, brief: ProjectBrief
    ) -> None:
        raise projects_unavailable()

    async def brief_failed(self, user_id: str, session_id: str, project_id: str, code: str) -> None:
        raise projects_unavailable()

    async def review_inputs(self, user_id: str, project_id: str) -> ReviewInputs:
        raise projects_unavailable()

    async def repo_text(self, user_id: str, session_id: str, url: str) -> str | None:
        raise projects_unavailable()

    async def save_review(
        self, user_id: str, session_id: str, project_id: str, outcome: ReviewOutcome
    ) -> None:
        raise projects_unavailable()

    async def save_drafts(
        self, user_id: str, session_id: str, project_id: str, drafts: list[DraftResult]
    ) -> None:
        raise projects_unavailable()


NO_PROJECTS: ProjectStore = _NoProjects()
