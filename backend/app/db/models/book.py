"""Édition d'un programme demandée par son propriétaire."""

from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime


class ProgramBook(UserScopedMixin, Base):
    __tablename__ = "program_books"
    __table_args__ = (UniqueConstraint("user_id", "program_id"),)

    program_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("programs.id", ondelete="CASCADE")
    )
    revision: Mapped[int] = mapped_column(default=0)
    source_hash: Mapped[str | None] = mapped_column(
        String(64), default=None, info={"export": False}
    )
    pdf_key: Mapped[str | None] = mapped_column(String(200), default=None)
    epub_key: Mapped[str | None] = mapped_column(String(200), default=None)
    chapters: Mapped[int] = mapped_column(default=0)
    rendered_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    failed: Mapped[bool] = mapped_column(default=False)
