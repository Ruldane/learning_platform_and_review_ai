"""Schémas de l'API des leçons et des ressources (SPEC 3.5, 3.6, 14.2 ; D91)."""

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.db.models.lessons import (
    MAX_LESSON_ATTEMPTS,
    LessonStatus,
    ResourceLevel,
    ResourceStatus,
    ResourceType,
)

# Les types littéraux sont réexportés : un router n'importe pas `app.db` (contrat 1b).
__all__ = [
    "LessonOut",
    "LessonPatch",
    "LessonStatus",
    "LessonSummaryOut",
    "ResourceLevel",
    "ResourceOut",
    "ResourcePatch",
    "ResourceStatus",
    "ResourceType",
    "LessonWriteIn",
]

TITLE_MAX = 200
MARKDOWN_MIN = 300  # une leçon des agents passe le Vérificateur (1 200 mots) ; ici un plancher
MARKDOWN_MAX = 60_000
RESOURCES_MAX = 12


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
        le=MAX_LESSON_ATTEMPTS,
        description=f"Essais de production faits ({MAX_LESSON_ATTEMPTS} au plus) : une leçon "
        f"`failed` avec moins de {MAX_LESSON_ATTEMPTS} essais sera relancée.",
    )
    word_count: int
    pdf_available: bool
    done_tasks: int = Field(ge=0, description="Tâches faites du module de la leçon (programme).")
    total_tasks: int = Field(ge=0, description="Tâches du module de la leçon.")
    completed: bool = Field(
        description="Toutes les tâches du module sont faites (au moins une) : leçon terminée."
    )
    verification_session_id: str | None = Field(
        default=None, description="Session de vérification d'une écriture directe en cours."
    )
    verification_failure_reason: str | None = Field(
        default=None, description="Motif du dernier échec de vérification d'une écriture directe."
    )


class LessonOut(LessonSummaryOut):
    program_id: str
    markdown: str
    failure_reason: str | None
    resources: list[ResourceOut]


class ResourcePatch(BaseModel):
    status: ResourceStatus


class ResourceWriteIn(BaseModel):
    """Un lien de lecture fourni avec une leçon, enregistré sans télécharger la page."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    url: HttpUrl
    title: str = Field(min_length=1, max_length=TITLE_MAX)
    type: ResourceType
    reason: str = Field(min_length=1, max_length=300)
    author: str | None = Field(default=None, min_length=1, max_length=200)
    date: str | None = Field(default=None, min_length=1, max_length=32)
    lang: str | None = Field(default=None, min_length=1, max_length=8)
    duration_minutes: int | None = Field(default=None, ge=1, le=600)
    level: ResourceLevel | None = None

    @field_validator("url")
    @classmethod
    def _no_credentials(cls, url: HttpUrl) -> HttpUrl:
        if url.username is not None or url.password is not None:
            raise ValueError("Le lien ne doit pas contenir d'identifiants.")
        return url


class LessonWriteIn(BaseModel):
    """Le brouillon d'un module soumis à la Fabrique. Par défaut, le titre du module est utilisé."""

    title: str | None = Field(default=None, min_length=1, max_length=TITLE_MAX)
    markdown: str = Field(min_length=MARKDOWN_MIN, max_length=MARKDOWN_MAX)
    resources: list[ResourceWriteIn] = Field(default_factory=list, max_length=RESOURCES_MAX)


class LessonPatch(BaseModel):
    """Retouche du titre ou du texte d'une leçon prête, ou ajout de ressources."""

    title: str | None = Field(default=None, min_length=1, max_length=TITLE_MAX)
    markdown: str | None = Field(default=None, min_length=MARKDOWN_MIN, max_length=MARKDOWN_MAX)
    resources: list[ResourceWriteIn] = Field(default_factory=list, max_length=RESOURCES_MAX)

    @model_validator(mode="after")
    def _something(self) -> "LessonPatch":
        if self.title is None and self.markdown is None and not self.resources:
            raise ValueError("rien à changer")
        return self
