from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.agents.tools.feynman_port import FeynmanCard, FeynmanExchange
from app.db.models.agents import SessionStatus


class FeynmanStart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    strong: bool = False


class FeynmanFileStart(FeynmanStart):
    path: Annotated[str, StringConstraints(min_length=1, max_length=250)]


class FeynmanSource(BaseModel):
    kind: Literal["lesson", "ide"]
    id: UUID
    title: str
    path: str | None = None


class FeynmanSaved(BaseModel):
    cards_added: int
    proof_saved: bool


class FeynmanReport(FeynmanExchange):
    summary: str
    cards: list[FeynmanCard]
    proof_skill: str | None
    saved: FeynmanSaved | None = None


class FeynmanData(BaseModel):
    source: FeynmanSource
    skill: str | None
    module_id: str | None = None
    report: FeynmanReport | None = None


class FeynmanRunOut(BaseModel):
    id: UUID
    session_id: UUID
    status: SessionStatus
    source: FeynmanSource
    report: FeynmanReport | None
