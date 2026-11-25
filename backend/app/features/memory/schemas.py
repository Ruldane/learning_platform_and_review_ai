"""Memory API schemas (14.2): items, log, search, documents."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.db.models.memory import (
    DocumentSourceKind,
    DocumentStatus,
    ItemStatus,
    MasteryLevel,
    MemoryKind,
    WriteAction,
)

# The literal types are re-exported: a router does not import `app.db` (contract 1b).
__all__ = [
    "AgentLevel",
    "ChunkOut",
    "DocumentCreated",
    "DocumentError",
    "DocumentOut",
    "DocumentSourceKind",
    "DocumentStatus",
    "ItemStatus",
    "LearnedStarted",
    "MapPoint",
    "MapResponse",
    "MemoryExport",
    "MemoryItemCreate",
    "MemoryItemDetail",
    "MemoryItemList",
    "MemoryItemOut",
    "MemoryItemPatch",
    "MemoryKind",
    "MemoryWriteOut",
    "MergeRequest",
    "PasteCreate",
    "NeighborOut",
    "ReindexState",
    "ReindexStatus",
    "SearchHitOut",
    "SearchRequest",
    "SearchResponse",
    "StatsOut",
    "UserWritableKind",
]

# Types a user creates by hand; the `lesson` and `source` ones come from the agents, the
# `document` ones from the import (`/documents`).
UserWritableKind = Literal["skill", "decision", "posting"]
# Levels that can be given by hand or by an agent: `validated` and `proven` are earned (phase 4).
AgentLevel = Literal["declared", "in_progress"]
Tag = Annotated[str, Field(min_length=1, max_length=40)]


class MemoryItemOut(BaseModel):
    id: str
    kind: MemoryKind
    title: str
    text: str
    tags: list[str]
    created_by: str
    session_id: str | None
    source_id: str | None
    lang: str | None
    status: ItemStatus
    level: MasteryLevel | None
    evidence: list[str]
    reason: str | None
    indexed: bool
    created_at: datetime
    updated_at: datetime


class MemoryItemList(BaseModel):
    items: list[MemoryItemOut]
    total: int


class ChunkOut(BaseModel):
    id: str
    ordinal: int
    text: str
    token_count: int


class NeighborOut(BaseModel):
    item_id: str
    title: str
    kind: MemoryKind
    score: float


class MemoryWriteOut(BaseModel):
    id: str
    item_id: str
    item_title: str
    action: WriteAction
    author: str
    session_id: str | None
    reason: str | None
    created_at: datetime


class LinkedNoteOut(BaseModel):
    item_id: str
    title: str


class MemoryItemDetail(MemoryItemOut):
    chunks: list[ChunkOut]
    neighbors: list[NeighborOut]
    writes: list[MemoryWriteOut]
    linked_notes: list[LinkedNoteOut] = Field(default_factory=list)


class MemoryItemCreate(BaseModel):
    kind: UserWritableKind
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=20_000)
    tags: list[Tag] = Field(default_factory=list, max_length=10)
    level: AgentLevel | None = None


class MemoryItemPatch(BaseModel):
    """Everything is optional; an absent or `null` field changes nothing. `status` only accepts
    `active`: confirming a pending decision (refusing it means deleting it)."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    text: str | None = Field(default=None, min_length=1, max_length=20_000)
    tags: list[Tag] | None = Field(default=None, max_length=10)
    level: AgentLevel | None = None
    status: Literal["active"] | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    kinds: list[MemoryKind] | None = None
    k: int = Field(default=8, ge=1, le=50)


class SearchHitOut(BaseModel):
    chunk_id: str
    item_id: str
    kind: MemoryKind
    title: str
    text: str
    score: float
    created_by: str


class SearchResponse(BaseModel):
    hits: list[SearchHitOut]
    agent_text: str


class DocumentError(BaseModel):
    """Readable import error; `item_id`: the item already in memory for a duplicate."""

    code: str
    message: str
    item_id: str | None = None


class DocumentOut(BaseModel):
    id: str
    name: str
    source_kind: DocumentSourceKind
    status: DocumentStatus
    error: DocumentError | None
    url: str | None
    size_bytes: int | None
    item_id: str | None
    learned: bool
    created_at: datetime
    updated_at: datetime


class DocumentCreated(BaseModel):
    document: DocumentOut
    duplicate: bool


class LearnedStarted(BaseModel):
    """`learned_document` session launched by `POST /documents/{id}/learned`."""

    session_id: str


class PasteCreate(BaseModel):
    """Pasted text (`POST /documents/text`, JSON body). The text length (500,000 characters at
    most) is checked by the service, which answers `paste_too_long`; the body is capped at
    21 MB by the middleware."""

    text: str
    title: str | None = Field(default=None, max_length=200)


# --- explorer: merge, map, statistics, reindexing, export (D67) -------------------------------


class MergeRequest(BaseModel):
    """Items to merge into the URL's item (same type, 20 at most)."""

    other_ids: list[str] = Field(min_length=1, max_length=20)


class MapPoint(BaseModel):
    item_id: str
    title: str
    kind: MemoryKind
    x: float
    y: float


class MapResponse(BaseModel):
    """One point per indexed active item (mean of its chunks), coordinates in [-1, 1];
    `truncated`: only the most recent are shown."""

    points: list[MapPoint]
    method: Literal["pca"]
    truncated: bool


ReindexStatus = Literal["idle", "queued", "running", "done", "failed"]


class ReindexState(BaseModel):
    """State of the user's reindexing, kept in memory (lost on restart)."""

    status: ReindexStatus
    done: int
    total: int
    error: str | None


class StatsOut(BaseModel):
    by_kind: dict[MemoryKind, int]
    total_items: int
    total_chunks: int
    pending_decisions: int
    unindexed_items: int
    last_write: MemoryWriteOut | None
    dimension: int
    vectorize_limit: int
    vectorize_share: float
    reindex: ReindexState
    dashboard_url: str


class MemoryExport(BaseModel):
    """The user's whole memory as JSON, without any vector."""

    version: Literal[1]
    exported_at: datetime
    items: list[MemoryItemOut]
    documents: list[DocumentOut]
    writes: list[MemoryWriteOut]
