from typing import Any

from pydantic import BaseModel, Field

from app.core.played import PlayClient


class PlayStart(BaseModel):
    launch: str = Field(min_length=1, max_length=64)
    arguments: dict[str, Any] = Field(default_factory=dict)
    played_by: PlayClient


class PlaySubmit(BaseModel):
    step_id: str = Field(min_length=36, max_length=36)
    response: str = Field(max_length=500_000)


class PlayLaunch(BaseModel):
    launch: str
    graph: str
    description: str
    input_schema: dict[str, Any]


class PlayBrief(BaseModel):
    session_id: str
    status: str
    played_by: PlayClient
    step_id: str | None = None
    expires_at: str | None = None
    agent: str | None = None
    messages: list[dict[str, Any]] = Field(default_factory=list)
    output_schema: dict[str, Any] | None = None
