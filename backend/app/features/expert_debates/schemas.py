from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.agents.tools.expert_debate_port import ExpertSpeech
from app.db.models.agents import SessionStatus


class ExpertDebateSummary(BaseModel):
    id: UUID
    session_id: UUID
    question: str
    status: SessionStatus
    created_at: datetime


class ExpertDebateOut(ExpertDebateSummary):
    speeches: list[ExpertSpeech]
    judgment: str | None


class ExpertDebateStarted(BaseModel):
    debate_id: UUID
    session_id: UUID


class ExpertJudgmentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4_000)]
