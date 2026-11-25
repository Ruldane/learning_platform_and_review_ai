"""Gap schemas (SPEC F8, D122): table recomputed on every read, most often missing skills and
"Add to the plan" (D123)."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.db.models.skills import SkillLevel
from app.features.gap.service.score import GapAction, GapSource


class GapRowOut(BaseModel):
    skill: str
    required: bool
    level: SkillLevel | None
    action: GapAction
    week: int | None  # week of the validated program (`in_program`)
    source: GapSource  # `cv_review`: spotted by the CV review (G3), outside the score


class GapOut(BaseModel):
    """`pending` while the analysis runs; `failed`: posting refused or analysis stopped."""

    posting_id: str
    status: Literal["pending", "ready", "failed"]
    score: int | None
    rows: list[GapRowOut]
    session_id: str | None


class TopMissingOut(BaseModel):
    skill: str
    postings: int  # postings that ask for it
    required_in: int  # dont obligatoire


class GapSkillsIn(BaseModel):
    skills: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(
        min_length=1, max_length=10
    )


class PlanGapIn(GapSkillsIn):
    """ "To add" or "Out of scope" lines and the chosen validated program."""

    program_id: Annotated[str, Field(min_length=36, max_length=36)] | None = None


class PlanGapStarted(BaseModel):
    session_id: str  # the `replan` replanning (`gap` trigger) to follow and validate


class ValidateGapStarted(BaseModel):
    """ "I already master them": the validation module added and its quiz being prepared."""

    module_id: str
    quiz_id: str
    session_id: str | None  # the Examiner session to follow
