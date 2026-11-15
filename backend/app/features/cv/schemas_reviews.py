"""Schémas des revues de CV, de leurs modifications et des versions produites (SPEC 5.3, 14.2 ;
D130). Les textes d'une modification (`before`, `after`) sont du CV de January : rendus à elle
seule, jamais journalisés ; une 422 nomme les champs (`details.fields`), jamais leur valeur."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.agents.tools.cv_indicators import AtsCheckId
from app.agents.tools.cv_review_port import ReviewReport
from app.agents.tools.cv_schema import ModificationAction, ModificationType, SectionKey
from app.db.models.career import ModificationStatus, ReviewStatus, VersionStatus

Decision = Literal["accepted", "refused"]


class ErrorDetailOut(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None


class ErrorOut(BaseModel):
    """L'enveloppe de toute erreur métier : `{error: {code, message, details}}`."""

    error: ErrorDetailOut


class ReviewStart(BaseModel):
    posting_id: str = Field(min_length=1, max_length=36)


class ReviewStarted(BaseModel):
    """Revue lancée : la revue (`running`) et sa session `cv_review` (à suivre par ses
    événements)."""

    review_id: str
    session_id: str


class AtsCheckOut(BaseModel):
    """Un contrôle de lisibilité par un ATS ; `detail` : phrase française sans texte du CV."""

    id: AtsCheckId
    passed: bool
    detail: str


class IndicatorsOut(BaseModel):
    """Couverture des exigences obligatoires de l'offre (`missing` : leur texte, tel que l'offre
    l'écrit) et contrôles ATS. Aucune garantie de passage n'est promise."""

    coverage_percent: int
    covered: int
    total: int
    missing: list[str]
    checks: list[AtsCheckOut]


class ModificationOut(BaseModel):
    """Une modification proposée. `ref` : « a3 » (Lecteur ATS) ou « r2 » (Recruteur) ; `before` :
    le texte visé dans le CV d'origine (vide pour un ajout ou un déplacement) ; `after` : le
    nouveau texte (pour `move`, la clé de la section avant laquelle `section` passe) ;
    `blocks` : pourquoi elle est « à confirmer » (phrases fixes) ; `fact_ids` : les faits du
    profil sur lesquels elle repose ; `author` : `ats_reader` ou `recruiter`."""

    id: str
    ref: str
    section: SectionKey
    action: ModificationAction
    type: ModificationType
    before: str
    after: str
    reason: str
    status: ModificationStatus
    blocks: list[str]
    fact_ids: list[str]
    author: str


class VersionOut(BaseModel):
    """Un CV produit pour une offre (`number` compte par offre). `indicators` : après le rendu
    (couverture des lignes adossées à un fait, contrôles ATS du PDF rendu), `None` avant ;
    `filename` : nom ASCII du PDF (`CV_<Nom>_<Entreprise>_<Poste>.pdf`) ; `decisions` : la
    décision de chaque modification au clic (`ref` → `accepted`, `refused`, `proposed`,
    `to_confirm`, ou `ignored` pour une acceptée que la composition n'a pas pu placer) ;
    `failure_reason` : phrase française d'un échec du rendu."""

    id: str
    review_id: str
    posting_id: str
    number: int
    status: VersionStatus
    page_count: int | None
    original_page_count: int
    allow_extra_pages: bool
    filename: str
    decisions: dict[str, str]
    indicators: IndicatorsOut | None
    created_at: datetime
    failure_reason: str | None


class CvReviewOut(BaseModel):
    """`before` : indicateurs du CV d'origine ; `gap_terms` : mots clés de l'offre que les faits
    cités ne portent pas, à appuyer par un fait ou à acquérir (ils n'entrent pas dans le CV) ;
    `waiting_output` : la session attend « Que veux-tu maintenant ? » (seul moment où
    « Générer le PDF » est possible)."""

    id: str
    posting_id: str
    status: ReviewStatus
    session_id: str | None
    before: IndicatorsOut | None
    modifications: list[ModificationOut]
    gap_terms: list[str]
    report: ReviewReport | None
    versions: list[VersionOut]
    waiting_output: bool
    created_at: datetime


class ModificationPatch(BaseModel):
    """Décision sur une modification. `after` : texte réécrit par January (revalidé contre le
    profil) ; `confirm` : « Je confirme que c'est vrai », seul moyen d'accepter une modification
    « à confirmer » (le fait entre alors au profil maître)."""

    status: Decision
    after: str | None = Field(default=None, min_length=1, max_length=600)
    confirm: bool = False

    @field_validator("after")
    @classmethod
    def _not_blank(cls, value: str | None) -> str | None:
        """Un texte fait seulement d'espaces est refusé (422 `fields: ["after"]`)."""
        if value is not None and not value.strip():
            raise ValueError("texte vide")
        return value


class BulkDecision(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=50)
    status: Decision


class BulkResult(BaseModel):
    """`skipped` : les modifications « à confirmer » (jamais acceptées en groupe) et les
    identifiants inconnus de la revue."""

    updated: int
    skipped: list[str]


class GenerateIn(BaseModel):
    """`allow_extra_pages` : garder un CV plus long que l'original plutôt que s'arrêter."""

    allow_extra_pages: bool = False


class GenerateStarted(BaseModel):
    version_id: str
