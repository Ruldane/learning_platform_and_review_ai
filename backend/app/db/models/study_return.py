"""The current resumption selection and its local reminder."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime


class StudyReturn(UserScopedMixin, Base):
    __tablename__ = "study_returns"
    __table_args__ = (UniqueConstraint("user_id"),)

    selection: Mapped[dict[str, Any] | None]
    prepared_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    reminder_on: Mapped[date | None] = mapped_column(Date)
    training_id: Mapped[str | None] = mapped_column(String(36))
