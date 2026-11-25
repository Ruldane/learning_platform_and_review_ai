"""Application kit schemas (SPEC 6.4, F16, D143): the seven pieces of a record, in the fixed order
of `KIT_ORDER`. A 422 names the fields, never the text sent (a piece is personal data)."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.agents.tools.kit_schema import KIT_KINDS as KIT_ORDER
from app.db.models.applications import KitKind as KitKind
from app.db.models.applications import KitStatus as KitStatus

CONTENT_MAX = 20_000
# `KIT_ORDER`: the fixed order of the pieces (F16), used by the list and the archive files.
__all__ = [
    "KIT_ORDER",
    "KitItemOut",
    "KitKind",
    "KitOut",
    "KitPatch",
    "KitSourceOut",
    "KitStartOut",
    "KitStatus",
]


class KitSourceOut(BaseModel):
    """A page read for the company file. `rank`: its number in the text (`[rank]`), from 1."""

    rank: int = Field(ge=1)
    url: str
    title: str | None


class KitItemOut(BaseModel):
    """A piece. `id`: `artifact_id` of the `artifact.ready` event (empty while the piece is not
    stored, status `pending`). `flags`: the terms the profile does not state (piece "to check").
    `salary_fields`: the salary answers left to January. `words`: the word count (the message for
    `linkedin`, both follow-ups together for `followups`). `error`: the readable reason of a
    failed piece. `sources`: the company file's pages (`company_brief`)."""

    id: str | None
    kind: KitKind
    status: KitStatus
    content: str
    flags: list[str]
    salary_fields: int
    words: int | None
    error: str | None
    sources: list[KitSourceOut]
    edited: bool
    updated_at: datetime | None


class KitOut(BaseModel):
    """A record's kit: always seven pieces, `pending` for those not stored yet. `session_id`: the
    open session, otherwise the last one; `running`: a session is open."""

    session_id: str | None
    running: bool
    items: list[KitItemOut]


class KitStartOut(BaseModel):
    session_id: str


class KitPatch(BaseModel):
    """January's text for the piece (empty allowed: the piece goes back to "to check")."""

    content: Annotated[str, Field(max_length=CONTENT_MAX)]
