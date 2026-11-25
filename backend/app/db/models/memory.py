from datetime import datetime
from typing import Any, Literal, get_args

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime
from app.db.models.skills import LEVEL_ORDER, SkillLevel

# Types shared with `app.agents`, which cannot import a feature (contract 6).
MemoryKind = Literal["document", "skill", "lesson", "source", "posting", "decision"]
MEMORY_KINDS: tuple[MemoryKind, ...] = get_args(MemoryKind)
PREVIOUS_MEMORY_KINDS: dict[MemoryKind, str] = {
    "skill": "acquis",
    "lesson": "lecon",
    "posting": "offre",
}
_CURRENT_MEMORY_KINDS = {old: kind for kind, old in PREVIOUS_MEMORY_KINDS.items()}
MasteryLevel = SkillLevel
MASTERY_ORDER: dict[MasteryLevel, int] = {level: rank for rank, level in enumerate(LEVEL_ORDER)}
ItemStatus = Literal["active", "pending"]
DocumentSourceKind = Literal["pdf", "docx", "markdown", "text", "url", "youtube", "paste"]
DocumentStatus = Literal["queued", "processing", "indexed", "error"]
WriteAction = Literal["create", "update", "delete", "confirm", "reject", "merge"]
USER_AUTHOR = "user"


def current_memory_kind(kind: str) -> str:
    return _CURRENT_MEMORY_KINDS.get(kind, kind)


class Document(UserScopedMixin, Base):
    """An imported document (file, link, pasted text) and the state of its ingestion.

    `name` is only a cleaned display name: never a path. The original file lives under
    `storage_key`. `source_hash` prevents importing the same content twice."""

    __tablename__ = "documents"
    # `uq_documents_user_id`: name that the `Base` convention gives to (user_id, source_hash).
    __table_args__ = (
        UniqueConstraint("user_id", "source_hash"),
        Index("ix_documents_user_status", "user_id", "status"),
    )

    name: Mapped[str] = mapped_column(String(200))
    source_kind: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    url: Mapped[str | None] = mapped_column(Text, default=None)
    storage_key: Mapped[str | None] = mapped_column(String(200), default=None)
    size_bytes: Mapped[int | None] = mapped_column(Integer, default=None)
    source_hash: Mapped[str] = mapped_column(String(64))
    item_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("memory_items.id", ondelete="SET NULL"), default=None
    )
    learned: Mapped[bool] = mapped_column(default=False)
    error: Mapped[dict[str, Any] | None] = mapped_column(default=None)  # {code, message}
    # Labels set by the feature that files the document (`cv`, `linkedin`: master profile,
    # D124), taken up by the `document` element at ingestion.
    tags: Mapped[list[Any]] = mapped_column(default=list)
    sync_metadata: Mapped[dict[str, Any] | None] = mapped_column(default=None)


class MemoryItem(UserScopedMixin, Base):
    """A memory item; the text is authoritative here, Qdrant is only its index.

    `meta` holds the level (`level`), the evidence (`evidence`) and the reason (`reason`).
    `content_hash` prevents saving the same content twice (see `content_hash`)."""

    __tablename__ = "memory_items"
    __table_args__ = (
        UniqueConstraint("user_id", "content_hash"),
        Index("ix_memory_items_user_kind", "user_id", "kind"),
        Index("ix_memory_items_user_status", "user_id", "status"),
    )

    kind: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(200))
    text: Mapped[str] = mapped_column(Text)
    tags: Mapped[list[Any]] = mapped_column(default=list)
    created_by: Mapped[str] = mapped_column(String(64))
    session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    source_id: Mapped[str | None] = mapped_column(String(36), default=None)
    lang: Mapped[str | None] = mapped_column(String(8), default=None)
    status: Mapped[str] = mapped_column(String(16), default="active")
    meta: Mapped[dict[str, Any]] = mapped_column(default=dict)
    content_hash: Mapped[str] = mapped_column(String(64))
    # `undo_volatile`: set by indexing, outside the MCP call; undo does not compare it
    # and resets it to empty (the item is reindexed, `app.mcp.undo`).
    indexed_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime, default=None, info={"undo_volatile": True}
    )


class MemoryChunk(UserScopedMixin, Base):
    """A fragment of an item; its `id` is the point identifier in Qdrant (UUID)."""

    __tablename__ = "memory_chunks"
    # `undo_derived`: the fragments are derived from the item's text; removing the item
    # (undo of an MCP addition) removes them with it; they do not count as rows that
    # depend on it.
    __table_args__ = (UniqueConstraint("item_id", "ordinal"), {"info": {"undo_derived": True}})

    item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("memory_items.id", ondelete="CASCADE")
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer)


class MemoryWrite(UserScopedMixin, Base):
    """A row of the write journal. It outlives the item: `item_id` has no foreign key and the
    title is copied (`item_title`)."""

    __tablename__ = "memory_writes"
    __table_args__ = (
        Index("ix_memory_writes_user_item", "user_id", "item_id"),
        Index("ix_memory_writes_user_created", "user_id", "created_at"),
    )

    item_id: Mapped[str] = mapped_column(String(36))
    item_title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(16))
    action: Mapped[str] = mapped_column(String(16))
    author: Mapped[str] = mapped_column(String(64))
    session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    reason: Mapped[str | None] = mapped_column(String(300), default=None)
