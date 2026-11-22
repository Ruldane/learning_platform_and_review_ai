"""Instantané d'une mission et preuve du rendu associé."""

from datetime import datetime
from typing import Any

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime


class Mission(UserScopedMixin, Base):
    __tablename__ = "missions"
    __table_args__ = (UniqueConstraint("user_id", "posting_id"),)

    posting_id: Mapped[str] = mapped_column(String(36))
    posting_title: Mapped[str | None] = mapped_column(String(200))
    company: Mapped[str | None] = mapped_column(String(200))
    deadline_at: Mapped[datetime] = mapped_column(UTCDateTime)
    revision: Mapped[int] = mapped_column(Integer)
    criteria: Mapped[list[Any]]
    submission: Mapped[dict[str, Any] | None]
