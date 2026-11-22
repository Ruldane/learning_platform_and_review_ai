from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

SurpriseId = Annotated[str, Field(min_length=36, max_length=36)]
SurpriseChatId = Annotated[str, Field(pattern=r"^[1-9][0-9]{0,18}$")]
SurpriseRole = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]


class SurprisePreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    token_id: SurpriseId | None = None
    role: SurpriseRole = ""


class SurpriseTokenOption(BaseModel):
    id: str
    label: str


class SurpriseSettingsOut(SurprisePreferences):
    telegram_ready: bool
    start: str | None
    end: str | None
    timezone: str | None
    tokens: list[SurpriseTokenOption]


class SurpriseChatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chat_id: SurpriseChatId


class SurpriseInvitationOut(BaseModel):
    id: str
    day: date


class SurpriseInviteOut(BaseModel):
    invitation: SurpriseInvitationOut | None = None


class SurpriseStartOut(BaseModel):
    interview_id: str
    session_id: str


class SurpriseQuestion(BaseModel):
    id: str
    text: str


class SurpriseDebrief(BaseModel):
    scores: dict[str, int]
    strengths: list[str]
    fixes: list[str]
    improved_answer: str


class SurpriseStateOut(BaseModel):
    status: Literal["invited", "preparing", "question", "done", "stopped", "failed"]
    question: SurpriseQuestion | None = None
    debrief: SurpriseDebrief | None = None


class SurpriseAnswerIn(SurpriseChatIn):
    question_id: Annotated[str, Field(min_length=1, max_length=100)]
    message_id: Annotated[str, Field(pattern=r"^[1-9][0-9]{0,18}$")]
    answer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class SurpriseAnswerOut(BaseModel):
    received: bool = True
