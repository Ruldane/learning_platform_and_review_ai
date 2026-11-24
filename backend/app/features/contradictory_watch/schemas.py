from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, StringConstraints, model_validator

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=140)]
Description = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=3000)
]


class WatchSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: AnyHttpUrl
    version: Title
    claim: Description

    @model_validator(mode="after")
    def address_without_credentials(self) -> Self:
        if self.url.username is not None or self.url.password is not None:
            raise ValueError("The source link must not contain credentials.")
        return self


class WatchExperimentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title
    sources: tuple[WatchSource, WatchSource]
    protocol: Description
    criterion: Description

    @model_validator(mode="after")
    def two_distinct_references(self) -> Self:
        first, second = self.sources
        if (first.url, first.version) == (second.url, second.version):
            raise ValueError("Choose two different references.")
        return self


class WatchObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    measurement: Description
    outcome: Literal["first", "second", "inconclusive"]


class WatchExperimentOut(WatchExperimentIn):
    id: UUID
    status: Literal["ready", "completed"]
    observation: WatchObservation | None = Field(default=None)
    created_at: datetime
