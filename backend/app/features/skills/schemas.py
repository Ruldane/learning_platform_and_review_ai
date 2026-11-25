"""Skills map contract (SPEC F15, D107): graph and radar, detail of a skill (evidence,
postings, next action), comparison with a target, curve."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.core.skills import EvidenceKind
from app.db.models.skills import SkillLevel

NextActionKind = Literal["study", "quiz", "review", "project"]
CompareTarget = Literal["goal", "posting"]  # target job; a specific posting (D123)

SkillName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]


class SkillCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: SkillName
    domain: SkillName | None = None
    synonyms: list[SkillName] = Field(default_factory=list, max_length=5)


class SkillCreated(BaseModel):
    id: str


class SkillNodeOut(BaseModel):
    id: str
    name: str
    domain: str  # "Other" without a domain
    level: SkillLevel | None  # `None`: no `user_skills` row (absent)
    demand: float | None  # share of the last radar run (0 to 1); `None` without a finished run
    evidence_count: int


class SkillEdgeOut(BaseModel):
    before_id: str
    after_id: str


class DomainScoreOut(BaseModel):
    domain: str
    score: int  # 0 to 100


class SkillGraphOut(BaseModel):
    nodes: list[SkillNodeOut]
    edges: list[SkillEdgeOut]
    domains: list[DomainScoreOut]


class EvidenceOut(BaseModel):
    kind: EvidenceKind
    label: str
    at: datetime | None  # `None`: phase 4 evidence, undated
    url: str | None  # path in the application; `None` without a page


class PostingRefOut(BaseModel):
    """A ready posting whose analysis cites the skill (D123); `url`: its page in the
    application."""

    id: str
    title: str
    url: str | None


class NextActionOut(BaseModel):
    kind: NextActionKind
    label: str
    url: str | None  # `None`: not available yet (evidence project)


class SkillDetailOut(BaseModel):
    id: str
    name: str
    domain: str
    synonyms: list[str]
    level: SkillLevel | None
    evidence: list[EvidenceOut]  # most recent first
    postings: list[PostingRefOut]  # 10 at most, most recent first
    next_action: NextActionOut | None  # `None`: proven skill


class CompareRowOut(BaseModel):
    skill_id: str
    name: str
    domain: str
    mine: SkillLevel | None
    target: SkillLevel
    gap: int  # target rank minus mine (absent = -1); 0 or less: reached


class CompareOut(BaseModel):
    target_label: str
    coverage: int  # share of the targets reached, in %
    rows: list[CompareRowOut]


class LevelCountsOut(BaseModel):
    declared: int
    in_progress: int
    validated: int
    proven: int


class HistoryPointOut(BaseModel):
    week_start: date  # Monday of the local week
    counts: LevelCountsOut
    score: int  # 0 to 100


class HistoryOut(BaseModel):
    points: list[HistoryPointOut]  # oldest to most recent; the current week live
