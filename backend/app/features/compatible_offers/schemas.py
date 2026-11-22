from pydantic import BaseModel

from app.features.gap.service import GapRowOut


class CompatibleOfferOut(BaseModel):
    title: str | None
    company: str | None
    url: str
    score: int
    rows: list[GapRowOut]


class CompatibleOfferPlan(BaseModel):
    program_id: str
    session_id: str
