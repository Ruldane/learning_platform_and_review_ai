from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Ref = Annotated[str, Field(min_length=1, max_length=36)]


class CalendarStatus(BaseModel):
    status: Literal["unconfigured", "disconnected", "connected", "revocation_pending"]


class ConnectIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consent: bool = Field(strict=True)


class OAuthLink(BaseModel):
    authorization_url: str


class StudySelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["study"]
    program_id: Ref
    source_id: Ref


class InterviewSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["interview"]
    source_id: Ref
    time: str = Field(pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
    minutes: int = Field(ge=15, le=180, strict=True)


Selection = Annotated[StudySelection | InterviewSelection, Field(discriminator="kind")]


class UpcomingEvent(BaseModel):
    id: str
    kind: Literal["study", "interview"]
    start: datetime
    end: datetime
    timezone: str


class CalendarProposalOut(BaseModel):
    id: str
    status: Literal["proposed", "synced"]
    action: Literal["add", "update", "unchanged"]
    kind: Literal["study", "interview"]
    title: str
    start: datetime
    end: datetime
    timezone: str
