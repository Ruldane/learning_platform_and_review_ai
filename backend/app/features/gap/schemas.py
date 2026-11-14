"""Schémas de l'écart (SPEC F8, D122) : tableau recalculé à chaque lecture, compétences qui
manquent le plus souvent et « Ajouter au planning » (D123)."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.db.models.skills import SkillLevel
from app.features.gap.service.score import GapAction, GapSource


class GapRowOut(BaseModel):
    skill: str
    required: bool
    level: SkillLevel | None
    action: GapAction
    week: int | None  # semaine du programme validé (`in_program`)
    source: GapSource  # `cv_review` : relevé par la revue du CV (G3), hors du score


class GapOut(BaseModel):
    """`pending` tant que l'analyse tourne ; `failed` : offre refusée ou analyse arrêtée."""

    posting_id: str
    status: Literal["pending", "ready", "failed"]
    score: int | None
    rows: list[GapRowOut]
    session_id: str | None


class TopMissingOut(BaseModel):
    skill: str
    postings: int  # offres qui la demandent
    required_in: int  # dont obligatoire


class PlanGapIn(BaseModel):
    """« Ajouter au planning » : des noms de lignes `to_add` de l'écart de l'offre."""

    skills: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(
        min_length=1, max_length=10
    )


class PlanGapStarted(BaseModel):
    session_id: str  # la replanification `replan` (déclencheur `gap`) à suivre et à valider
