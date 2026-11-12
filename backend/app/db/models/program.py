from datetime import date, datetime
from typing import Any, Literal

from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

# Types partagés avec `app.agents`, qui ne peut pas importer une feature (contrat 6).
TaskType = Literal["lire", "regarder", "pratiquer", "quiz", "projet"]
TaskStatus = Literal["todo", "done"]
ProgramStatus = Literal["draft", "validated"]


class Program(UserScopedMixin, Base):
    """Un programme d'apprentissage (SPEC 3.4) : brouillon du Stratège, puis validé par January."""

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


class Module(UserScopedMixin, Base):
    """Un module d'une semaine ; `skipped` : sujet déjà acquis, gardé pour l'historique."""

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


class Task(UserScopedMixin, Base):
    """Une tâche planifiée un jour précis ; `already_known` : révision d'un acquis (20 min)."""

    __tablename__ = "tasks"
    # `ix_tasks_user_planned` : le calendrier et la vue du jour lisent par utilisateur et date.
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
    """Une version du plan (instantané et différence avec la précédente).

    `(user_id, session_id, revision)` rend l'écriture du Stratège idempotente au rejeu.
    """

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
