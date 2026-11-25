"""Quick capture and journal schemas (SPEC F18, D108). A 422 never copies the input back
(common handler: paths and messages only)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.db.models.study import JournalKind

__all__ = [
    "CaptureRequest",
    "CaptureStarted",
    "JournalEntryOut",
    "JournalKind",
    "JournalLinksOut",
    "JournalPage",
]

TEXT_MAX = 20_000
URL_MAX = 2048


class CaptureRequest(BaseModel):
    """A single source: an http(s) link, a text, or an already imported document
    (`POST /documents`). Zero or several: 422 `invalid_input`."""

    url: str | None = Field(default=None, max_length=URL_MAX)
    text: str | None = Field(default=None, max_length=TEXT_MAX)
    document_id: str | None = Field(default=None, max_length=36)


class CaptureStarted(BaseModel):
    session_id: str


class JournalLinksOut(BaseModel):
    session_id: str | None
    study_session_id: str | None
    study_session_kind: Literal["guided", "training"] | None = None
    quiz_attempt_id: str | None
    quiz_id: str | None = None
    ide_session_id: str | None = None
    ide_run_id: str | None = None
    memory_item_id: str | None


class JournalEntryOut(BaseModel):
    id: str
    kind: JournalKind
    text: str
    occurred_on: date  # jour de January (son fuseau, D98)
    created_at: datetime
    links: JournalLinksOut


class JournalPage(BaseModel):
    """The rows, most recent first; `next_before`: cursor of the next page (`?before=`),
    `None` on the last."""

    entries: list[JournalEntryOut]
    next_before: str | None
