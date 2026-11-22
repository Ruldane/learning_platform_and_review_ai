"""Décisions datées et mesure du retour, dans le compte qui les a planifiées."""

from datetime import date, datetime

from sqlalchemy import Date, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime


class DatedCommitment(UserScopedMixin, Base):
    __tablename__ = "dated_commitments"
    __table_args__ = (UniqueConstraint("user_id", "request_id"),)

    request_id: Mapped[str] = mapped_column(String(36))
    title: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(80))
    intention: Mapped[str] = mapped_column(Text)
    indicator: Mapped[str] = mapped_column(String(160))
    unit: Mapped[str] = mapped_column(String(40))
    target: Mapped[str] = mapped_column(String(32))
    due_on: Mapped[date] = mapped_column(Date)
    observed: Mapped[str | None] = mapped_column(String(32))
    note: Mapped[str | None] = mapped_column(Text)
    reviewed_on: Mapped[date | None] = mapped_column(Date)
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
