from datetime import date
from typing import Any

from sqlalchemy import Boolean, Date, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin


class OfflineReview(UserScopedMixin, Base):
    __tablename__ = "offline_reviews"
    __table_args__ = (UniqueConstraint("user_id", "receipt_id"),)

    receipt_id: Mapped[str] = mapped_column(String(36))
    card_id: Mapped[str] = mapped_column(String(36))
    due_date: Mapped[date] = mapped_column(Date)
    ok: Mapped[bool] = mapped_column(Boolean)
    response: Mapped[dict[str, Any] | None] = mapped_column(default=None)
