"""Tables du quotidien (phase 8, D157) : mini projets, relevés du radar du marché, briefs du jour
et registre persistant des passages planifiés."""

from datetime import date, datetime
from typing import Any, Literal

from sqlalchemy import Date, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

# Types partagés avec `app.agents`, qui ne peut pas importer une feature (contrat 6).
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
    """Le mini projet d'un module (P1). `module_id` et `program_id` n'ont pas de clé étrangère :
    le projet survit à une replanification. `submissions` : les rendus (au plus 10), `evaluation` :
    la dernière évaluation, `drafts` : les brouillons par type (`DraftKind`)."""

    __tablename__ = "projects"
    # `uq_projects_user_id` : (user_id, module_id), un projet par module.
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
    """Un relevé du radar. `role_norm` et `zone_norm` : le poste et la zone normalisés, clés de
    comparaison avec le relevé précédent (`previous_id`). `blocked_domains` : domaine → nombre,
    jamais journalisé. `postings` : une entrée par offre examinée (D157)."""

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


class Brief(UserScopedMixin, Base):
    """Le brief d'un jour local : un instantané (`sections`), plus la ressource et le conseil
    écrits par les agents. `offer_keys` : les liens d'offres montrés (clés normalisées)."""

    __tablename__ = "briefs"
    # `uq_briefs_user_id` : (user_id, day), un brief par jour local.
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
    """Un passage d'une tâche planifiée pour une période (P13) : le registre persistant, par
    `(user_id, name, period)`. APScheduler reste en mémoire."""

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
