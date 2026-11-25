"""Daily tables (phase 8, D157): mini projects, market radar readings, daily briefs and the
persistent register of scheduled runs."""

from datetime import date, datetime
from typing import Any, Literal

from sqlalchemy import Date, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

# Types shared with `app.agents`, which cannot import a feature (contract 6).
ProjectStatus = Literal[
    "brief_pending", "brief_failed", "todo", "reviewing", "to_redo", "validated"
]
DraftKind = Literal["cv_line", "profile_entry", "linkedin_post", "readme_plan"]
DraftStatus = Literal["ready", "to_check"]
RadarStatus = Literal["running", "done", "failed"]
RadarTrigger = Literal["schedule", "manual"]
PostingRead = Literal["ok", "blocked", "not_posting", "extract_failed"]
BriefOrigin = Literal["schedule", "opening"]
AdviceStatus = Literal["pending", "ready", "failed", "unavailable"]
JobStatus = Literal["running", "done", "failed", "skipped"]


class Project(UserScopedMixin, Base):
    """The mini project of a module (P1). `module_id` and `program_id` have no foreign key: the
    project survives a replanning. `submissions`: the submissions (at most 10), `evaluation`:
    the latest evaluation, `drafts`: the drafts by type (`DraftKind`)."""

    __tablename__ = "projects"
    # `uq_projects_user_id`: (user_id, module_id), one project per module.
    __table_args__ = (UniqueConstraint("user_id", "module_id"),)

    module_id: Mapped[str] = mapped_column(String(36))
    program_id: Mapped[str] = mapped_column(String(36))
    title: Mapped[str] = mapped_column(String(200))
    brief: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(String(16), default="brief_pending")
    session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    brief_attempts: Mapped[int] = mapped_column(Integer, default=0)
    submissions: Mapped[list[Any]] = mapped_column(default=list)
    evaluation: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    drafts: Mapped[dict[str, Any]] = mapped_column(default=dict)
    validated_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    profile_version: Mapped[int | None] = mapped_column(Integer, default=None)


class RadarRun(UserScopedMixin, Base):
    """A radar reading. `role_norm` and `zone_norm`: the normalized role and area, keys for
    comparison with the previous reading (`previous_id`). `blocked_domains`: domain -> count,
    never logged. `postings`: one entry per offer reviewed (D157)."""

    __tablename__ = "radar_runs"
    __table_args__ = (Index("ix_radar_runs_user_created", "user_id", "created_at"),)

    role: Mapped[str] = mapped_column(String(120))
    zone: Mapped[str] = mapped_column(String(120))
    role_norm: Mapped[str] = mapped_column(String(120))
    zone_norm: Mapped[str] = mapped_column(String(120))
    trigger: Mapped[str] = mapped_column(String(16))
    period: Mapped[str | None] = mapped_column(String(16), default=None)
    status: Mapped[str] = mapped_column(String(16), default="running")
    session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    queries: Mapped[int] = mapped_column(Integer, default=0)
    candidates: Mapped[int] = mapped_column(Integer, default=0)
    read_count: Mapped[int] = mapped_column(Integer, default=0)
    blocked_count: Mapped[int] = mapped_column(Integer, default=0)
    not_postings: Mapped[int] = mapped_column(Integer, default=0)
    analyzed: Mapped[int] = mapped_column(Integer, default=0)
    blocked_domains: Mapped[dict[str, Any]] = mapped_column(default=dict)
    postings: Mapped[list[Any]] = mapped_column(default=list)
    ranking: Mapped[list[Any]] = mapped_column(default=list)
    alerts: Mapped[list[Any]] = mapped_column(default=list)
    previous_id: Mapped[str | None] = mapped_column(String(36), default=None)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    # Code of a failed reading (`search_unavailable`, `session_failed`…): never a message.
    error_code: Mapped[str | None] = mapped_column(String(64), default=None)


class Brief(UserScopedMixin, Base):
    """The brief of a local day: a snapshot (`sections`), plus the resource and the advice written
    by the agents. `offer_keys`: the offer links shown (normalized keys)."""

    __tablename__ = "briefs"
    # `uq_briefs_user_id`: (user_id, day), one brief per local day.
    __table_args__ = (UniqueConstraint("user_id", "day"),)

    day: Mapped[date] = mapped_column(Date)
    origin: Mapped[str] = mapped_column(String(16))
    sections: Mapped[dict[str, Any]] = mapped_column(default=dict)
    offer_keys: Mapped[list[Any]] = mapped_column(default=list)
    resource: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    advice: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    advice_status: Mapped[str] = mapped_column(String(16), default="pending")
    session_id: Mapped[str | None] = mapped_column(String(36), default=None)


class JobRun(UserScopedMixin, Base):
    """A run of a scheduled task for a period (P13): the persistent register, by
    `(user_id, name, period)`. APScheduler stays in memory."""

    __tablename__ = "jobs"
    # `uq_jobs_user_id` : (user_id, name, period).
    __table_args__ = (
        UniqueConstraint("user_id", "name", "period"),
        Index("ix_jobs_user_name_started", "user_id", "name", "started_at"),
    )

    name: Mapped[str] = mapped_column(String(40))
    period: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="running")
    started_at: Mapped[datetime] = mapped_column(UTCDateTime)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    error_code: Mapped[str | None] = mapped_column(String(64), default=None)
    ref_id: Mapped[str | None] = mapped_column(String(36), default=None)
    next_due_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
