"""Types du débat et port de stockage des prises de parole."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, Field, HttpUrl

from app.core.errors import AppError

EXPERT_GRAPH = "expert_debate"
EXPERT_SCOPE = "expert_debate"
ExpertRole = Literal["researcher", "practitioner", "skeptic"]
EXPERT_ROLES: tuple[ExpertRole, ...] = ("researcher", "practitioner", "skeptic")


class ExpertCitation(BaseModel):
    index: int = Field(ge=1)
    title: str
    url: HttpUrl


class ExpertSpeech(BaseModel):
    role: ExpertRole
    text: str
    citations: list[ExpertCitation]


@dataclass(frozen=True)
class ExpertDraft:
    question: str
    strong: bool
    used_tokens: int
    saved: bool


class ExpertDebateStore(Protocol):
    async def draft(
        self, user_id: str, session_id: str, thread_id: str, turn_id: str
    ) -> ExpertDraft: ...

    async def publish(
        self,
        user_id: str,
        session_id: str,
        thread_id: str,
        turn_id: str,
        speeches: Sequence[ExpertSpeech],
    ) -> None: ...


class _NoDebate:
    async def draft(
        self, user_id: str, session_id: str, thread_id: str, turn_id: str
    ) -> ExpertDraft:
        raise AppError("debate_unavailable", "The expert debate is unavailable.", 503)

    async def publish(
        self,
        user_id: str,
        session_id: str,
        thread_id: str,
        turn_id: str,
        speeches: Sequence[ExpertSpeech],
    ) -> None:
        raise AppError("debate_unavailable", "The expert debate is unavailable.", 503)


NO_EXPERT_DEBATE: ExpertDebateStore = _NoDebate()
