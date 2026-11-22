from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.agents.tools.conversation_port import ConversationSource
from app.db.models.agents import SessionStatus

MAX_QUESTION = 2_000
MAX_PASSAGE = 1_000


class ConversationMessageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    question: Annotated[str, StringConstraints(min_length=1, max_length=MAX_QUESTION)]
    passage: Annotated[str, StringConstraints(min_length=1, max_length=MAX_PASSAGE)] | None = None
    passage_occurrence: Annotated[int, Field(strict=True, ge=0, le=150_000)] | None = None
    strong: Annotated[bool, Field(strict=True)] = False

    @model_validator(mode="after")
    def normalize(self) -> Self:
        self.question = self.question.strip()
        if self.passage is not None:
            self.passage = " ".join(self.passage.split())
        if not self.question or self.passage == "":
            raise ValueError("La question et le passage éventuel doivent contenir du texte.")
        if self.passage_occurrence is not None and self.passage is None:
            raise ValueError("Une occurrence doit désigner un passage.")
        return self


class ConversationStarted(BaseModel):
    session_id: UUID


class ConversationTurnOut(BaseModel):
    id: UUID
    request_id: UUID
    session_id: UUID
    question: str
    passage: str | None
    passage_occurrence: int | None
    answer: str | None
    status: SessionStatus
    sources: list[ConversationSource]


class ConversationUsage(BaseModel):
    thread_tokens: int
    thread_token_limit: int
    day_tokens: int
    day_token_limit: int
    turns: int
    turn_limit: int


class LessonConversationOut(BaseModel):
    id: UUID
    lesson_id: UUID
    turns: list[ConversationTurnOut]
    usage: ConversationUsage
