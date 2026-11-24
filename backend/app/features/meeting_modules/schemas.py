from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

ExcerptKind = Literal["decision", "topic"]


class MeetingModuleIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=140)]
    transcript: Annotated[str, Field(min_length=1, max_length=16000)]


class MeetingExcerpt(BaseModel):
    line: int
    kind: ExcerptKind
    text: str


class MeetingSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lines: Annotated[list[Annotated[int, Field(ge=1)]], Field(max_length=6)]

    @model_validator(mode="after")
    def unique_lines(self) -> Self:
        if len(self.lines) != len(set(self.lines)):
            raise ValueError("Each line must be selected only once.")
        return self


class MeetingStudyStep(BaseModel):
    source_line: int
    instruction: str
    criterion: str
    minutes: int


class MeetingModuleOut(BaseModel):
    id: UUID
    title: str
    source_digest: str
    status: Literal["draft", "published"]
    excerpts: list[MeetingExcerpt]
    selection: list[int]
    steps: list[MeetingStudyStep]
    published_at: datetime | None


class MeetingModuleSummary(BaseModel):
    id: UUID
    title: str
    status: Literal["draft", "published"]
    created_at: datetime
