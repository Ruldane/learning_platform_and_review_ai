"""Schémas des offres (SPEC F8, 14.2, D122). Une 422 ne recopie jamais la saisie (gestionnaire
commun : chemins et messages seulement ; erreurs métier : `details.fields` seulement)."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from app.agents.tools.posting_schema import PostingLevel
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
    level: PostingLevel
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


_Name = Annotated[str, Field(min_length=1, max_length=80)]


class RequirementIn(BaseModel):
    text: str = Field(min_length=3, max_length=300)
    required: bool
    skills: list[_Name] = Field(default_factory=list, max_length=6)


class KeywordIn(BaseModel):
    term: str = Field(min_length=2, max_length=80)
    variants: list[_Name] = Field(default_factory=list, max_length=5)


class EliminatoryIn(BaseModel):
    kind: Literal["experience_years", "location", "language", "degree", "other"]
    text: str = Field(min_length=3, max_length=200)


class SkillNeedIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    required: bool
    domain: str | None = Field(default=None, max_length=60)
    learnable: bool = True


class PostingAnalysisIn(BaseModel):
    """L'analyse d'une offre écrite à la main ou par Claude (aucun agent) : les mêmes champs et les
    mêmes bornes que celle de l'Analyste. Chaque mot clé doit figurer tel quel dans le texte de
    l'offre, et chaque exigence obligatoire nomme des compétences listées dans `skills` (sinon 422
    `posting_analysis_invalid`, qui nomme le champ)."""

    title: str = Field(min_length=2, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    level: PostingLevel = "unknown"
    location: str | None = Field(default=None, max_length=120)
    remote: str | None = Field(default=None, max_length=60)
    language: str = Field(default="fr", pattern=r"^[a-z]{2}$")
    requirements: list[RequirementIn] = Field(default_factory=list, max_length=40)
    keywords: list[KeywordIn] = Field(default_factory=list, max_length=40)
    eliminatory: list[EliminatoryIn] = Field(default_factory=list, max_length=10)
    tools: list[_Name] = Field(default_factory=list, max_length=30)
    skills: list[SkillNeedIn] = Field(default_factory=list, max_length=40)
    apply_url: str | None = Field(default=None, max_length=URL_MAX)


class PostingDirectIn(PostingAnalysisIn):
    """Une offre écrite en direct : son texte (copie figée, 300 caractères et 50 mots au moins), son
    lien s'il y en a un (jamais lu : rien n'est téléchargé), et son analyse."""

    text: str = Field(max_length=TEXT_MAX)
    url: str | None = Field(default=None, max_length=URL_MAX)


class PostingPatch(BaseModel):
    """Retouche de l'analyse d'une offre : les champs donnés remplacent ceux de l'analyse (une liste
    donnée remplace toute la liste), qui est revalidée en entier. Le texte figé ne change pas."""

    title: str | None = Field(default=None, min_length=2, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    level: PostingLevel | None = None
    location: str | None = Field(default=None, max_length=120)
    remote: str | None = Field(default=None, max_length=60)
    language: str | None = Field(default=None, pattern=r"^[a-z]{2}$")
    requirements: list[RequirementIn] | None = Field(default=None, max_length=40)
    keywords: list[KeywordIn] | None = Field(default=None, max_length=40)
    eliminatory: list[EliminatoryIn] | None = Field(default=None, max_length=10)
    tools: list[_Name] | None = Field(default=None, max_length=30)
    skills: list[SkillNeedIn] | None = Field(default=None, max_length=40)
    apply_url: str | None = Field(default=None, max_length=URL_MAX)

    @model_validator(mode="after")
    def _something(self) -> "PostingPatch":
        if not self.model_dump(exclude_none=True):
            raise ValueError("rien à changer")
        return self
