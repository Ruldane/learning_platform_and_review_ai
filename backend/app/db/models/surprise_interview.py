"""Consent and interview invitations through Nod's private chat."""

from datetime import date
from typing import Any

from sqlalchemy import Date, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin


class SurpriseSettings(UserScopedMixin, Base):
    __tablename__ = "surprise_interview_settings"
    __table_args__ = (UniqueConstraint("user_id"),)

    enabled: Mapped[bool]
    token_id: Mapped[str | None] = mapped_column(String(36))
    chat_consent_id: Mapped[str | None] = mapped_column(String(36))
    consent_id: Mapped[str] = mapped_column(String(36))
    role: Mapped[str] = mapped_column(String(200))


class SurpriseInvitation(UserScopedMixin, Base):
    __tablename__ = "surprise_interview_invitations"
    __table_args__ = (UniqueConstraint("user_id", "week"),)

    week: Mapped[date] = mapped_column(Date())
    day: Mapped[date] = mapped_column(Date())
    consent_id: Mapped[str] = mapped_column(String(36))
    role: Mapped[str] = mapped_column(String(200))
    answers: Mapped[dict[str, Any]] = mapped_column(default=dict)
