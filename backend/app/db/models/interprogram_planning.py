"""Propositions de semaine commune et confirmation de leur application."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime


class SharedWeekProposal(UserScopedMixin, Base):
    __tablename__ = "shared_week_proposals"
    __table_args__ = (UniqueConstraint("user_id", "week_start", "selection_key", "fingerprint"),)

    week_start: Mapped[date] = mapped_column(Date)
    selection_key: Mapped[str] = mapped_column(String(64))
    fingerprint: Mapped[str] = mapped_column(String(64))
    document: Mapped[dict[str, Any]]
    accepted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
