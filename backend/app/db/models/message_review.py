"""Account consent and the daily booking of a card for Nod."""

from datetime import date
from typing import Any

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin


class TelegramReviewSettings(UserScopedMixin, Base):
    __tablename__ = "telegram_review_settings"
    __table_args__ = (UniqueConstraint("user_id"),)

    enabled: Mapped[bool]
    start: Mapped[str] = mapped_column(String(5))
    end: Mapped[str] = mapped_column(String(5))
    token_id: Mapped[str | None] = mapped_column(String(36))
    chat_id: Mapped[str | None] = mapped_column(String(19))
    consent_id: Mapped[str] = mapped_column(String(36))


class TelegramReviewChallenge(UserScopedMixin, Base):
    __tablename__ = "telegram_review_challenges"
    __table_args__ = (UniqueConstraint("user_id", "day"),)

    day: Mapped[date] = mapped_column(Date())
    consent_id: Mapped[str] = mapped_column(String(36))
    card_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("flashcards.id", ondelete="CASCADE")
    )
    rating: Mapped[str | None] = mapped_column(String(4))
    outcome: Mapped[dict[str, Any] | None]
