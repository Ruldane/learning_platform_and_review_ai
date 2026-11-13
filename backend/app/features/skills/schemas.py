"""Contrat de la carte de compétences (SPEC F15, D107) : graphe et radar, détail d'une
compétence (preuves, offres, prochaine action), comparaison avec une cible, courbe."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from app.core.skills import EvidenceKind
from app.db.models.skills import SkillLevel

NextActionKind = Literal["study", "quiz", "review", "project"]
CompareTarget = Literal["goal"]  # « offre précise » en phase 6


class SkillNodeOut(BaseModel):
    id: str
    name: str
    domain: str  # « Autres » sans domaine
    level: SkillLevel | None  # `None` : aucune ligne `user_skills` (absente)
    demand: float | None  # de 0 à 1 ; `None` jusqu'au Radar (phase 8)
    evidence_count: int


class SkillEdgeOut(BaseModel):
    before_id: str
    after_id: str


class DomainScoreOut(BaseModel):
    domain: str
    score: int  # 0 à 100


class SkillGraphOut(BaseModel):
    nodes: list[SkillNodeOut]
    edges: list[SkillEdgeOut]
    domains: list[DomainScoreOut]


class EvidenceOut(BaseModel):
    kind: EvidenceKind
    label: str
    at: datetime | None  # `None` : preuve de la phase 4, sans date
    url: str | None  # chemin dans l'application ; `None` sans page


class PostingRefOut(BaseModel):
    """Une offre qui exige la compétence (phase 6) ; liste vide d'ici là."""

    id: str
    title: str
    url: str | None


class NextActionOut(BaseModel):
    kind: NextActionKind
    label: str
    url: str | None  # `None` : pas encore disponible (projet preuve)


class SkillDetailOut(BaseModel):
    id: str
    name: str
    domain: str
    synonyms: list[str]
    level: SkillLevel | None
    evidence: list[EvidenceOut]  # la plus récente d'abord
    postings: list[PostingRefOut]
    next_action: NextActionOut | None  # `None` : compétence prouvée


class CompareRowOut(BaseModel):
    skill_id: str
    name: str
    domain: str
    mine: SkillLevel | None
    target: SkillLevel
    gap: int  # rang de la cible moins le mien (absente = −1) ; 0 ou moins : atteint


class CompareOut(BaseModel):
    target_label: str
    coverage: int  # part des cibles atteintes, en %
    rows: list[CompareRowOut]


class LevelCountsOut(BaseModel):
    declare: int
    en_cours: int
    valide: int
    prouve: int


class HistoryPointOut(BaseModel):
    week_start: date  # lundi de la semaine locale
    counts: LevelCountsOut
    score: int  # 0 à 100


class HistoryOut(BaseModel):
    points: list[HistoryPointOut]  # du plus ancien au plus récent ; la semaine en cours en direct
