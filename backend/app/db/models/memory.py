from datetime import datetime
from typing import Any, Literal, get_args

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

# Types partagés avec `app.agents`, qui ne peut pas importer une feature (contrat 6).
MemoryKind = Literal["document", "acquis", "lecon", "source", "offre", "decision"]
MEMORY_KINDS: tuple[MemoryKind, ...] = get_args(MemoryKind)
MasteryLevel = Literal["declare", "en_cours", "valide", "prouve"]
MASTERY_ORDER: dict[MasteryLevel, int] = {"declare": 0, "en_cours": 1, "valide": 2, "prouve": 3}
ItemStatus = Literal["active", "pending"]
DocumentSourceKind = Literal["pdf", "docx", "markdown", "text", "url", "youtube", "paste"]
DocumentStatus = Literal["queued", "processing", "indexed", "error"]
WriteAction = Literal["create", "update", "delete", "confirm", "reject", "merge"]
USER_AUTHOR = "user"


class Document(UserScopedMixin, Base):
    """Un document importé (fichier, lien, texte collé) et l'état de son ingestion.

    `name` n'est qu'un nom d'affichage nettoyé : jamais un chemin. Le fichier d'origine vit
    sous `storage_key`. `source_hash` empêche d'importer deux fois le même contenu.
    """

    __tablename__ = "documents"
    # `uq_documents_user_id` : nom que la convention de `Base` donne à (user_id, source_hash).
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


class MemoryItem(UserScopedMixin, Base):
    """Un élément de la mémoire ; le texte fait foi ici, Qdrant n'en est que l'index.

    `meta` porte le niveau (`level`), les preuves (`evidence`) et la raison (`reason`).
    `content_hash` empêche d'enregistrer deux fois le même contenu (voir `content_hash`).
    """

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
    indexed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)


class MemoryChunk(UserScopedMixin, Base):
    """Un fragment d'élément ; son `id` est l'identifiant du point dans Qdrant (UUID)."""

    __tablename__ = "memory_chunks"
    __table_args__ = (UniqueConstraint("item_id", "ordinal"),)

    item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("memory_items.id", ondelete="CASCADE")
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer)


class MemoryWrite(UserScopedMixin, Base):
    """Une ligne du journal d'écriture. Survit à l'élément : `item_id` n'a pas de clé étrangère
    et le titre est copié (`item_title`)."""

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
