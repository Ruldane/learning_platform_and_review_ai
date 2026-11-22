"""Contrôles privés rattachés à l'instantané d'une preuve de compétence."""

from datetime import date, datetime
from typing import Any, Literal

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

TransferStage = Literal["scheduled", "preparing", "ready", "grading", "complete"]


class SkillTransfer(Base, UserScopedMixin):
    __tablename__ = "skill_transfers"
    __table_args__ = (UniqueConstraint("user_id", "skill_id", "proof_id", "due_on"),)

    skill_id: Mapped[str] = mapped_column(String(36), ForeignKey("skills.id", ondelete="CASCADE"))
    proof_id: Mapped[str] = mapped_column(String(64))
    proof: Mapped[dict[str, Any]]
    due_on: Mapped[date] = mapped_column(Date)
    stage: Mapped[TransferStage] = mapped_column(String(12), default="scheduled")
    session_id: Mapped[str | None] = mapped_column(String(36))
    exercise: Mapped[dict[str, Any] | None]
    answer: Mapped[str | None] = mapped_column(Text)
    assessment: Mapped[dict[str, Any] | None]
    assessed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
