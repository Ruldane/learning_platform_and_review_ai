from datetime import date
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

ChatId = Annotated[str, Field(pattern=r"^[1-9][0-9]{0,18}$")]
RecordId = Annotated[str, Field(min_length=36, max_length=36)]
LocalTime = Annotated[str, Field(pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")]


class TelegramReviewPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    enabled: bool = False
    start: LocalTime = "18:00"
    end: LocalTime = "20:00"
    token_id: RecordId | None = None
    chat_id: ChatId | None = None

    @model_validator(mode="after")
    def check_consent(self) -> Self:
        if self.start >= self.end:
            raise ValueError("The end must follow the start on the same day.")
        if self.enabled and (self.token_id is None or self.chat_id is None):
            raise ValueError("Choose the Nod token and the private chat.")
        return self


class NodTokenOption(BaseModel):
    id: str
    label: str


class TelegramReviewSettingsOut(TelegramReviewPreferences):
    timezone: str
    tokens: list[NodTokenOption]


class TelegramClaimIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chat_id: ChatId


class TelegramChallenge(BaseModel):
    id: str
    day: date
    question: str


class TelegramClaimOut(BaseModel):
    challenge: TelegramChallenge | None = None


class TelegramRevealOut(BaseModel):
    answer: str


class TelegramAnswerIn(TelegramClaimIn):
    result: Literal["ok", "fail"]


class TelegramAnswerOut(BaseModel):
    step: int
    due_date: date
