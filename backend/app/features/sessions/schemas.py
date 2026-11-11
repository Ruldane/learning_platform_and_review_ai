from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.agents.runtime.events import InterruptRequestedPayload, RunFailedPayload
from app.db.models.agents import SessionStatus

__all__ = [
    "MessageRequest",
    "ResumeRequest",
    "SessionStatus",
    "SessionView",
    "StartSessionRequest",
    "StartSessionResponse",
]


class StartSessionRequest(BaseModel):
    graph: str = Field(min_length=1, max_length=64)
    input: dict[str, Any] = Field(default_factory=dict)
    subject_type: str | None = Field(default=None, max_length=32)
    subject_id: str | None = Field(default=None, max_length=36)


class StartSessionResponse(BaseModel):
    session_id: str


class SessionView(BaseModel):
    """État d'une session pour le front ; `last_seq` : dernier événement écrit (le WebSocket
    reprend avec `after_seq`)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    graph: str
    status: SessionStatus
    last_seq: int
    pending_interrupt: InterruptRequestedPayload | None
    error: RunFailedPayload | None
    tokens_in: int
    tokens_out: int
    cost_usd: float
    created_at: datetime
    updated_at: datetime


class ResumeRequest(BaseModel):
    """Réponse à la question en attente (`interrupt_id` de `pending_interrupt`), ou reprise
    d'une pause (`interrupt_id` nul)."""

    interrupt_id: str | None = None
    value: Any = None


class MessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
