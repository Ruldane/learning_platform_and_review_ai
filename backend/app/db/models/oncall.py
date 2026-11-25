"""Simulated on-call exercises and log, separated by account."""

from typing import Any

from sqlalchemy import Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin


class OncallIncident(UserScopedMixin, Base):
    __tablename__ = "oncall_incidents"
    __table_args__ = (
        Index(
            "uq_oncall_running_diagnostic",
            "user_id",
            unique=True,
            sqlite_where=text("diagnostic_state = 'running'"),
        ),
    )

    kind: Mapped[str] = mapped_column(String(20))
    seed: Mapped[int] = mapped_column(Integer)
    alert_at: Mapped[int] = mapped_column(Integer)
    ide_session_id: Mapped[str] = mapped_column(String(36))
    minute: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=0)
    events: Mapped[list[Any]] = mapped_column(default=list)
    observed_events: Mapped[list[Any]] = mapped_column(default=list)
    diagnostic_run_id: Mapped[str | None] = mapped_column(String(36), default=None)
    diagnostic_state: Mapped[str] = mapped_column(String(16), default="idle")
    diagnostic_hash: Mapped[str | None] = mapped_column(String(64), default=None)
    report: Mapped[str | None] = mapped_column(Text, default=None)
    review_session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    review_context: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    verdict: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    proof_recorded: Mapped[bool] = mapped_column(default=False)
