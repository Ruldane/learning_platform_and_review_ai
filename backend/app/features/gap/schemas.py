"""Schémas de l'écart (SPEC F8, D122) : tableau recalculé à chaque lecture et compétences qui
manquent le plus souvent."""

from typing import Literal

from pydantic import BaseModel

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
