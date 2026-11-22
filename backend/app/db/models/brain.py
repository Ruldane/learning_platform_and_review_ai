from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin


class BrainFolder(UserScopedMixin, Base):
    """Racine déclarée par l'utilisatrice, accessible au seul relais de son compte."""

    __tablename__ = "brain_folders"
    __table_args__ = (UniqueConstraint("user_id", "path"),)

    name: Mapped[str] = mapped_column(String(200))
    path: Mapped[str] = mapped_column(Text, info={"export": False})
    paused: Mapped[bool] = mapped_column(default=False)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    report: Mapped[dict[str, Any] | None] = mapped_column(default=None)


class BrainFile(UserScopedMixin, Base):
    """Un fichier du dossier, avec son document courant dans la mémoire."""

    __tablename__ = "brain_files"
    __table_args__ = (UniqueConstraint("folder_id", "path"),)

    folder_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brain_folders.id", ondelete="CASCADE")
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), unique=True
    )
    path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)


class BrainSyncToken(UserScopedMixin, Base):
    """Une seule identité de synchronisation active par compte, hors export et hors MCP."""

    __tablename__ = "brain_sync_tokens"
    __table_args__ = (UniqueConstraint("user_id"), {"info": {"export": False}})

    token_hash: Mapped[str] = mapped_column(String(64))
