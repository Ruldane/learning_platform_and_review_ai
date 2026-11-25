from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.agents.runtime.events import InterruptRequestedPayload, RunFailedPayload, UserCommand
from app.db.models.agents import SessionStatus

__all__ = [
    "MessageRequest",
    "ResumeRequest",
    "SessionStatus",
    "SessionView",
    "StartSessionRequest",
    "StartSessionResponse",
    "UserCommand",
]


class StartSessionRequest(BaseModel):
    graph: str = Field(min_length=1, max_length=64)
    input: dict[str, Any] = Field(default_factory=dict)
    subject_type: str | None = Field(default=None, max_length=32)
    subject_id: str | None = Field(default=None, max_length=36)


class StartSessionResponse(BaseModel):
    session_id: str


class SessionView(BaseModel):
    """State of a session for the front; `last_seq`: last event written (the WebSocket
    resumes with `after_seq`); `subject_type`/`subject_id`: the tracked subject (a document for
    the Archivist), to resume tracking it after a reload (D71)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    graph: str
    status: SessionStatus
    subject_type: str | None
    subject_id: str | None
    played_by: str | None = None
    last_seq: int
    pending_interrupt: InterruptRequestedPayload | None
    error: RunFailedPayload | None
    tokens_in: int
    tokens_out: int
    cost_usd: float
    created_at: datetime
    updated_at: datetime


class ResumeRequest(BaseModel):
    """Answer to the pending question (`interrupt_id` of `pending_interrupt`), or resuming
    from a pause (null `interrupt_id`)."""

    interrupt_id: str | None = None
    value: Any = None


class MessageRequest(BaseModel):
    """Message from the user, or a debate command (D82): the text is then optional.
    Empty (or blank) text without a command: 422 `invalid_input` (`SessionsService.message`)."""

    text: str = Field(default="", max_length=4000)
    command: UserCommand | None = None
