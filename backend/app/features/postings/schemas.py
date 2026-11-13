"""Schémas des offres (SPEC F8, 14.2, D122). Une 422 ne recopie jamais la saisie (gestionnaire
commun : chemins et messages seulement ; erreurs métier : `details.fields` seulement)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.db.models.postings import PostingSource, PostingStatus

URL_MAX = 2048
TEXT_MAX = 60_000

DuplicateLevelOut = Literal["certain", "probable", "possible"]


class PostingIn(BaseModel):
    """Exactement une source : le lien de l'offre ou son texte collé ; sinon 422
    `posting_source`."""

    url: str | None = Field(default=None, max_length=URL_MAX)
    text: str | None = Field(default=None, max_length=TEXT_MAX)


class DistinctIn(BaseModel):
    other_id: str = Field(min_length=1, max_length=36)


class DuplicateOut(BaseModel):
    level: DuplicateLevelOut
    posting_id: str
    title: str | None
    company: str | None
    created_at: datetime  # dans le fuseau de January


class RequirementOut(BaseModel):
    text: str
    required: bool
    skills: list[str]


class KeywordOut(BaseModel):
    term: str
    variants: list[str]


class EliminatoryOut(BaseModel):
    kind: Literal["experience_years", "location", "language", "degree", "other"]
    text: str


class SkillNeedOut(BaseModel):
    name: str
    required: bool
    domain: str | None
    learnable: bool


class PostingAnalysisOut(BaseModel):
    """L'analyse de l'Analyste (`PostingAnalysis`, D121), telle qu'elle est rangée."""

    title: str
    company: str | None
    level: Literal["junior", "confirme", "senior", "lead", "inconnu"]
    location: str | None
    remote: str | None
    language: str
    requirements: list[RequirementOut]
    keywords: list[KeywordOut]
    eliminatory: list[EliminatoryOut]
    tools: list[str]
    skills: list[SkillNeedOut]
    apply_url: str | None


class PostingSummaryOut(BaseModel):
    id: str
    title: str | None
    company: str | None
    status: PostingStatus  # `failed` aussi pour une analyse interrompue (D122)
    source: PostingSource
    score: int | None  # score de match (F8), dès que l'écart est rangé
    created_at: datetime
    has_review: bool


class PostingOut(PostingSummaryOut):
    url: str | None
    text: str  # copie figée lue à l'ajout
    analysis: PostingAnalysisOut | None
    # Doublons probables et possibles, connus après l'analyse (G35) ; « certain » : la réponse
    # 200 de `POST /postings`.
    duplicates: list[DuplicateOut]
    failure_reason: str | None
    gap_session_id: str | None


class PostingCreatedOut(BaseModel):
    """`created` faux : même lien ou même texte (doublon « certain »), l'offre existante ;
    `session_id` : l'analyse lancée (ou relancée), sinon `None`."""

    posting: PostingOut
    created: bool
    session_id: str | None


class GapStarted(BaseModel):
    session_id: str
