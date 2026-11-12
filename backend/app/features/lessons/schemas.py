"""Schémas de l'API des leçons et des ressources (SPEC 3.5, 3.6, 14.2 ; D91)."""

from pydantic import BaseModel, Field

from app.db.models.lessons import LessonStatus, ResourceLevel, ResourceStatus, ResourceType

# Les types littéraux sont réexportés : un router n'importe pas `app.db` (contrat 1b).
__all__ = [
    "LessonOut",
    "LessonStatus",
    "LessonSummaryOut",
    "ResourceLevel",
    "ResourceOut",
    "ResourcePatch",
    "ResourceStatus",
    "ResourceType",
]


class ResourceOut(BaseModel):
    """Une ressource d'un module : lien, métadonnées de la source (auteur, date, langue) et
    raison du choix ; `has_local_copy` : PDF libre gardé sur le disque
    (`GET /resources/{id}/file`), sinon `note` est la fiche de lecture."""

    id: str
    module_id: str
    program_id: str
    type: ResourceType
    title: str
    url: str
    author: str | None
    date: str | None = Field(description="Date de publication telle que la source la donne.")
    lang: str | None
    duration_minutes: int | None
    level: ResourceLevel | None
    reason: str
    score: int | None
    status: ResourceStatus
    has_local_copy: bool
    note: str | None


class LessonSummaryOut(BaseModel):
    id: str
    module_id: str
    week_rank: int
    title: str
    status: LessonStatus = Field(
        description="`pending` : pas encore lancée (semaines 3 et suivantes : 7 jours avant leur "
        "début) ; `generating` ; `ready` ; `failed` (relancée automatiquement, 3 essais en tout)."
    )
    attempts: int = Field(
        ge=0,
        le=3,
        description="Essais de production faits (3 au plus) : une leçon `failed` avec moins de 3 "
        "essais sera relancée.",
    )
    word_count: int
    pdf_available: bool


class LessonOut(LessonSummaryOut):
    program_id: str
    markdown: str
    failure_reason: str | None
    resources: list[ResourceOut]


class ResourcePatch(BaseModel):
    status: ResourceStatus
