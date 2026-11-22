"""Port du responsable d'exploitation vers les exercices simulés."""

from typing import Protocol

from pydantic import BaseModel, Field

from app.core.errors import AppError

REVIEW_GRAPH = "oncall_review"
SUBJECT = "oncall_incident"


class ReviewScore(BaseModel):
    diagnosis: int = Field(ge=0, le=5)
    evidence: int = Field(ge=0, le=5)
    correction: int = Field(ge=0, le=5)
    prevention: int = Field(ge=0, le=5)
    feedback: str = Field(min_length=1, max_length=2_000)

    @property
    def total(self) -> int:
        return self.diagnosis + self.evidence + self.correction + self.prevention

    @property
    def accepted(self) -> bool:
        return self.total >= 14 and min(self.diagnosis, self.evidence, self.correction) >= 3


class ReviewInput(BaseModel):
    kind: str
    minute: int
    observations: list[dict[str, object]]
    report: str
    previous: ReviewScore | None = None


class OncallPort(Protocol):
    async def read(self, user_id: str, incident_id: str, session_id: str) -> ReviewInput: ...

    async def record(
        self, user_id: str, incident_id: str, session_id: str, score: ReviewScore
    ) -> bool: ...


class _Unavailable:
    async def read(self, user_id: str, incident_id: str, session_id: str) -> ReviewInput:
        raise AppError("oncall_unavailable", "Le simulateur d’astreinte est indisponible.", 503)

    async def record(
        self, user_id: str, incident_id: str, session_id: str, score: ReviewScore
    ) -> bool:
        raise AppError("oncall_unavailable", "Le simulateur d’astreinte est indisponible.", 503)


NO_ONCALL: OncallPort = _Unavailable()
