from datetime import date, datetime
from typing import Any, Literal

from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

# Types shared with `app.agents`, which cannot import a feature (contract 6).
TaskType = Literal["read", "watch", "practice", "quiz", "project"]
TaskStatus = Literal["todo", "done"]
ProgramStatus = Literal["draft", "validated"]
Stage = Literal["foundations", "practice", "advanced"]
PlanKind = Literal["build", "replan"]
# `empty` and `impossible` (D106): proposals closed as soon as they are written (nothing to
# change, impossible to file), never shown as « à valider ».
PlanStatus = Literal["accepted", "pending", "refused", "superseded", "empty", "impossible"]


class Program(UserScopedMixin, Base):
    """A learning program (SPEC 3.4): draft from the Strategist, then validated by January."""

    __tablename__ = "programs"

    goal_id: Mapped[str] = mapped_column(String(36), ForeignKey("goals.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    start_date: Mapped[date] = mapped_column(Date)
    weekly_minutes: Mapped[int] = mapped_column(Integer)
    cap_minutes: Mapped[int] = mapped_column(Integer)
    session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    validated_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)


class Week(UserScopedMixin, Base):
    __tablename__ = "weeks"
    # `uq_weeks_program_id` : (program_id, rank).
    __table_args__ = (UniqueConstraint("program_id", "rank"),)

    program_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("programs.id", ondelete="CASCADE")
    )
    rank: Mapped[int] = mapped_column(Integer)
    theme: Mapped[str] = mapped_column(String(200))
    objective: Mapped[str] = mapped_column(Text)
    deliverable: Mapped[str] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date)
    # The week’s stage in the book and the reason for its position.
    stage: Mapped[str | None] = mapped_column(String(16), default=None)
    rationale: Mapped[str | None] = mapped_column(Text, default=None)


class Module(UserScopedMixin, Base):
    """A module of one week; `skipped`: topic already known, kept for history."""

    __tablename__ = "modules"
    # `uq_modules_week_id` : (week_id, rank).
    __table_args__ = (UniqueConstraint("week_id", "rank"),)

    week_id: Mapped[str] = mapped_column(String(36), ForeignKey("weeks.id", ondelete="CASCADE"))
    program_id: Mapped[str] = mapped_column(String(36))
    rank: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    skills: Mapped[list[Any]] = mapped_column(default=list)
    prerequisites: Mapped[list[Any]] = mapped_column(default=list)
    skipped: Mapped[bool] = mapped_column(default=False)
    # « validation »: « Valider mes acquis » module (quiz without lesson); otherwise null.
    kind: Mapped[str | None] = mapped_column(String(16), default=None)
    # Pages of the official documentation (leading the lesson's starting addresses) and old APIs
    # (to be shown only in the « Lire du code ancien » box).
    official_urls: Mapped[list[Any]] = mapped_column(default=list, server_default="[]")
    legacy: Mapped[list[Any]] = mapped_column(default=list, server_default="[]")


class Task(UserScopedMixin, Base):
    """A task planned for a specific day; `already_known`: review of a known topic (20 min)."""

    __tablename__ = "tasks"
    # `ix_tasks_user_planned`: the calendar and the day view read by user and date.
    __table_args__ = (Index("ix_tasks_user_planned", "user_id", "planned_date"),)

    module_id: Mapped[str] = mapped_column(String(36), ForeignKey("modules.id", ondelete="CASCADE"))
    program_id: Mapped[str] = mapped_column(String(36), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(16))
    minutes: Mapped[int] = mapped_column(Integer)
    done_criterion: Mapped[str] = mapped_column(Text)
    planned_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(8), default="todo")
    already_known: Mapped[bool] = mapped_column(default=False)


class PlanVersion(UserScopedMixin, Base):
    """A version of the plan (snapshot and difference with the previous one).

    `(user_id, session_id, revision)` makes the Strategist's write idempotent on replay."""

    __tablename__ = "plan_versions"
    # `uq_plan_versions_program_id` et `uq_plan_versions_user_id`.
    __table_args__ = (
        UniqueConstraint("program_id", "version"),
        UniqueConstraint("user_id", "session_id", "revision"),
    )

    program_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("programs.id", ondelete="CASCADE")
    )
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict[str, Any]] = mapped_column(default=dict)
    diff: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    reason: Mapped[str] = mapped_column(String(300), default="")
    session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    revision: Mapped[int | None] = mapped_column(Integer, default=None)
    accepted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    # Phase 5 (D99). `build`: version from the Strategist or January; `replan`: weekly review.
    # `pending`: proposal awaiting January, never read as "the current plan".
    kind: Mapped[str] = mapped_column(String(8), default="build", server_default="build")
    status: Mapped[str] = mapped_column(String(12), default="pending", server_default="pending")
    base_fingerprint: Mapped[str | None] = mapped_column(String(64), default=None)
    review_entry_id: Mapped[str | None] = mapped_column(String(36), default=None)
    week_loads: Mapped[dict[str, Any] | None] = mapped_column(default=None)
