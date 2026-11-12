"""Port des leçons (D90). `app.agents` n'importe aucune feature (contrat 6) : il décrit ici ce dont
le parcours `lesson_factory` a besoin (la fiche du module, la publication de la leçon et de ses
ressources, l'échec, le module suivant) ; la feature `lessons` l'implémentera (tâche 4.10).

Chaque écriture est idempotente par module : un nœud rejoué après un arrêt (SPEC 9.4) réécrit la
même chose, jamais une leçon ni une ressource de plus.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field

from app.core.errors import AppError
from app.db.models.lessons import ResourceLevel, ResourceType

MAX_SEED_URLS = 5


@dataclass(frozen=True)
class ModuleBrief:
    """Le module dont on écrit la leçon, tel que le programme l'a fixé."""

    module_id: str
    program_id: str
    title: str
    skills: tuple[str, ...]
    prerequisites: tuple[str, ...]
    week_rank: int
    week_theme: str
    goal_text: str  # l'objectif de January, pour situer la leçon
    language: str  # langue de la leçon (`lesson_language` des réglages)
    # Pages des praticiens et sources retenues du Conseil liées au module (5 au plus).
    seed_urls: tuple[str, ...]


class ResourcePick(BaseModel):
    """Une ressource retenue pour le module (SPEC 3.6) : une source notée 60 ou plus de la
    session. Auteur, date et langue sont lus par le port sur la source, jamais par le modèle."""

    source_id: str
    type: ResourceType
    duration_minutes: int = Field(ge=1, le=600)
    level: ResourceLevel
    reason: str = Field(min_length=5, max_length=200)


class ResourcePicks(BaseModel):
    resources: list[ResourcePick] = Field(min_length=3, max_length=6)


@dataclass(frozen=True)
class LessonReport:
    """Rapport du Vérificateur rangé avec la leçon. À la publication `unsupported` est vide et
    `problems` ne garde que des remarques sans gravité (par exemple des ressources en nombre
    insuffisant)."""

    words: int
    unsupported: tuple[str, ...]
    problems: tuple[str, ...]
    revisions: int


@dataclass(frozen=True)
class PublishedLesson:
    lesson_id: str
    pdf_ok: bool  # le PDF a pu être produit ; sinon la leçon se lit quand même dans l'application
    resources: int


class LessonStore(Protocol):
    async def brief(self, user_id: str, module_id: str) -> ModuleBrief:
        """La fiche du module de l'utilisateur ; `module_not_found` (404) s'il n'est pas à lui."""
        ...

    async def publish(
        self,
        user_id: str,
        session_id: str,
        module_id: str,
        *,
        markdown: str,
        resources: Sequence[ResourcePick],
        report: LessonReport,
    ) -> PublishedLesson:
        """Range la leçon prête, ses ressources et son PDF ; idempotent par module : rejoué, il
        rend la même leçon sans écrire de ligne de plus."""
        ...

    async def fail(self, user_id: str, session_id: str, module_id: str, reason: str) -> None:
        """Marque la leçon du module en échec, avec une raison lisible ; idempotent."""
        ...

    async def next_module(
        self, user_id: str, program_id: str, *, exclude_session_id: str
    ) -> str | None:
        """Fait suivre la chaîne : lance la leçon du prochain module dû du programme et rend son
        id, ou `None` s'il n'en reste pas. `exclude_session_id` : la session en cours, qui ne
        compte pas comme une chaîne déjà ouverte. Idempotent (une seule chaîne par programme)."""
        ...


def lessons_unavailable() -> AppError:
    return AppError("lessons_unavailable", "Les leçons ne sont pas branchées sur ce moteur.", 503)


class _NoLessons:
    """Valeur par défaut du moteur (tests existants, démarrages sans la feature `lessons`)."""

    async def brief(self, user_id: str, module_id: str) -> ModuleBrief:
        raise lessons_unavailable()

    async def publish(
        self,
        user_id: str,
        session_id: str,
        module_id: str,
        *,
        markdown: str,
        resources: Sequence[ResourcePick],
        report: LessonReport,
    ) -> PublishedLesson:
        raise lessons_unavailable()

    async def fail(self, user_id: str, session_id: str, module_id: str, reason: str) -> None:
        raise lessons_unavailable()

    async def next_module(
        self, user_id: str, program_id: str, *, exclude_session_id: str
    ) -> str | None:
        raise lessons_unavailable()


NO_LESSONS: LessonStore = _NoLessons()
