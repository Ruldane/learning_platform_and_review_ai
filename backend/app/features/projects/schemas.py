"""Contrat des mini projets (SPEC 14.2, P1 à P3, P19, D166). Une 422 nomme les champs, jamais leur
valeur (description, lien de dépôt, texte d'un brouillon : des données personnelles, 17.2)."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.db.models.daily import DraftKind, DraftStatus, ProjectStatus

__all__ = [
    "CriterionOut",
    "DraftKind",
    "DraftOut",
    "DraftPatchIn",
    "DraftStatus",
    "EvaluationOut",
    "ProfileEntryIn",
    "ProjectBriefOut",
    "ProjectOut",
    "ProjectStatus",
    "ProjectSummary",
    "SessionStarted",
    "SubmissionOut",
]

CONTENT_MAX = 3_000
# Les textes de l'entrée de projet sont rognés avant d'être mesurés : un nom ou une réalisation
# blancs sont une 422, jamais une erreur du profil (D166).
_STRIP = {"strip_whitespace": True}
EntryName = Annotated[str, StringConstraints(**_STRIP, min_length=1, max_length=120)]
EntryLine = Annotated[str, StringConstraints(**_STRIP, min_length=1, max_length=200)]
EntryText = Annotated[str, StringConstraints(**_STRIP, max_length=600)]


class ProjectBriefOut(BaseModel):
    """L'énoncé écrit par le Praticien."""

    title: str
    context: str
    objective: str
    constraints: list[str]
    criteria: list[str]
    hours: int
    deliverable: Literal["repo", "description", "either"]


class SubmissionOut(BaseModel):
    """Un rendu. `screenshots` : le nombre de captures (`GET /projects/{id}/screenshots/{n}`)."""

    at: datetime
    repo_url: str | None
    description: str | None
    screenshots: int


class CriterionOut(BaseModel):
    index: int
    criterion: str
    met: bool
    comment: str


class EvaluationOut(BaseModel):
    """La dernière évaluation : le verdict est celui du code. `repo_status` : le dépôt a-t-il pu
    être lu ? (`none` : aucun lien donné)."""

    at: datetime | None
    verdict: Literal["validated", "to_redo"]
    results: list[CriterionOut]
    feedback: str
    repo_status: Literal["read", "unreadable", "none"]


class ProfileEntryIn(BaseModel):
    """L'entrée de projet du profil maître : le texte de January, éventuellement modifié."""

    name: EntryName
    description: EntryText = ""
    achievements: list[EntryLine] = Field(default_factory=list, max_length=4)


class DraftOut(BaseModel):
    """Un brouillon au nom de January. `to_check` : `flags` nomme ce que son profil et son projet
    ne disent pas (ou la longueur). `edited` : January l'a retouché."""

    kind: DraftKind
    status: DraftStatus
    content: str
    entry: ProfileEntryIn | None
    flags: list[str]
    edited: bool


class ProjectOut(BaseModel):
    id: str
    module_id: str
    program_id: str
    title: str
    status: ProjectStatus
    brief: ProjectBriefOut | None
    submissions: list[SubmissionOut]
    evaluation: EvaluationOut | None
    drafts: list[DraftOut]
    validated_at: datetime | None
    profile_version: int | None
    session_id: str | None


class ProjectSummary(BaseModel):
    """Une ligne du Portfolio. `week` (à partir de 1) et `rank` (dans la semaine, comme `GET
    /programs`) : la place du module dans son programme (`None` si le module n'existe plus)."""

    id: str
    module_id: str
    program_id: str
    program_title: str | None
    title: str
    status: ProjectStatus
    week: int | None
    rank: int | None
    hours: int | None
    skills: list[str]
    validated_at: datetime | None
    profile_version: int | None
    session_id: str | None


class SessionStarted(BaseModel):
    session_id: str


class DraftPatchIn(BaseModel):
    """Un brouillon retouché : `entry` pour l'entrée de projet, `content` pour les trois autres.
    Un seul des deux, selon le type."""

    content: str | None = Field(default=None, min_length=1, max_length=CONTENT_MAX)
    entry: ProfileEntryIn | None = None
