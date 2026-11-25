"""Contract for paper readings and their experiment."""

from typing import Literal

from pydantic import BaseModel, HttpUrl, field_validator


class PaperLabCreate(BaseModel):
    url: HttpUrl

    @field_validator("url")
    @classmethod
    def public_address(cls, url: HttpUrl) -> HttpUrl:
        if url.username or url.password:
            raise ValueError("Use a public address without credentials.")
        return url


class PaperLabStarted(BaseModel):
    lab_id: str
    session_id: str


class PaperLabSummary(BaseModel):
    id: str
    url: str
    title: str | None
    stage: Literal["queued", "ready", "failed"]


class PaperLabOut(PaperLabSummary):
    source_title: str | None
    course: str | None
    expected: str | None
    ide_session_id: str | None
    session_id: str
