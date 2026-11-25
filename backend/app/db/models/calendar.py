"""Separate Calendar authorization and previews to confirm."""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime


class CalendarConnection(UserScopedMixin, Base):
    __tablename__ = "calendar_connections"
    __table_args__ = (UniqueConstraint("user_id"), {"info": {"export": False}})

    oauth_state_hash: Mapped[str | None] = mapped_column(String(64), default=None)
    oauth_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(
        Text, default=None, info={"export": False}
    )
    revoke_pending: Mapped[bool] = mapped_column(Boolean, default=False)
    generation: Mapped[str | None] = mapped_column(String(36), default=None)


class CalendarProposal(UserScopedMixin, Base):
    __tablename__ = "calendar_proposals"

    connection_generation: Mapped[str] = mapped_column(String(36))
    event_id: Mapped[str] = mapped_column(String(64), info={"export": False})
    source_hash: Mapped[str] = mapped_column(String(64), info={"export": False})
    starts_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    payload: Mapped[dict[str, Any]]
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    synced_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
