"""Tentative et remise du Boss de fin de programme."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime


class BossAttempt(UserScopedMixin, Base):
    __tablename__ = "boss_attempts"
    __table_args__ = (UniqueConstraint("user_id", "program_id"),)

    program_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("programs.id", ondelete="CASCADE")
    )
    ide_session_id: Mapped[str] = mapped_column(String(36))
    started_at: Mapped[datetime] = mapped_column(UTCDateTime)
    change_at: Mapped[datetime] = mapped_column(UTCDateTime)
    deadline_at: Mapped[datetime] = mapped_column(UTCDateTime)
    brief: Mapped[str] = mapped_column(Text)
    change: Mapped[str] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    submitted_files: Mapped[dict[str, str] | None] = mapped_column(JSON, default=None)
    sandbox_run_id: Mapped[str | None] = mapped_column(String(36), default=None)
    review_session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    diagnostic: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    verdict: Mapped[dict[str, Any] | None] = mapped_column(JSON(none_as_null=True), default=None)
    proof_recorded: Mapped[bool] = mapped_column(Boolean, default=False)
