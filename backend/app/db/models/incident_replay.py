from typing import Any

from sqlalchemy import JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin


class IncidentReplay(UserScopedMixin, Base):
    __tablename__ = "incident_replays"
    __table_args__ = (UniqueConstraint("user_id", "receipt"),)

    receipt: Mapped[str] = mapped_column(String(36))
    scenario: Mapped[str] = mapped_column(String(48))
    title: Mapped[str] = mapped_column(String(180))
    timeline: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    notes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
