from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.agents.tools.conversation_port import ClassmateReply, ConversationSource, FocusOutcome
from app.db.models.agents import SessionStatus

MAX_QUESTION = 2_000
MAX_PASSAGE = 1_000
MAX_TITLE = 120
ChatScope = Literal["brain", "training"]


class ConversationSummary(BaseModel):
    id: UUID
    title: str
    updated_at: datetime


class ConversationRename(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_TITLE)
    ]


class ConversationQuestionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    question: Annotated[str, StringConstraints(min_length=1, max_length=MAX_QUESTION)]
    strong: Annotated[bool, Field(strict=True)] = False

    @model_validator(mode="after")
    def normalize_question(self) -> Self:
        self.question = self.question.strip()
        if not self.question:
            raise ValueError("La question doit contenir du texte.")
        return self


class ConversationMessageIn(ConversationQuestionIn):
    passage: Annotated[str, StringConstraints(min_length=1, max_length=MAX_PASSAGE)] | None = None
    passage_occurrence: Annotated[int, Field(strict=True, ge=0, le=150_000)] | None = None

    @model_validator(mode="after")
    def normalize_passage(self) -> Self:
        if self.passage is not None:
            self.passage = " ".join(self.passage.split())
        if self.passage == "":
            raise ValueError("Le passage doit contenir du texte.")
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
    classmates: list[ClassmateReply] | None = None
    focus_outcome: FocusOutcome | None = None


class ConversationUsage(BaseModel):
    thread_tokens: int
    thread_token_limit: int
    day_tokens: int
    day_token_limit: int
    turns: int
    turn_limit: int


class ConversationOut(BaseModel):
    id: UUID
    turns: list[ConversationTurnOut]
    usage: ConversationUsage


class LessonConversationOut(ConversationOut):
    lesson_id: UUID
