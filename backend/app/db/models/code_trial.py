"""Project version and verdict kept per account."""

from typing import Any

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin


class CodeTrial(UserScopedMixin, Base):
    __tablename__ = "code_trials"
    __table_args__ = (UniqueConstraint("user_id", "ide_session_id", "files_version"),)

    ide_session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ide_sessions.id", ondelete="CASCADE")
    )
    session_id: Mapped[str] = mapped_column(String(36))
    title: Mapped[str] = mapped_column(String(200))
    files_version: Mapped[int]
    snapshot: Mapped[dict[str, str]] = mapped_column(JSON)
    pleadings: Mapped[list[Any] | None] = mapped_column(JSON(none_as_null=True))
    verdict_choice: Mapped[str | None] = mapped_column(String(16))
    verdict_reason: Mapped[str | None] = mapped_column(String(2000))
