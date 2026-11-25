"""Application tables (phase 7, D138): records, event thread, contacts, follow-ups, kit pieces,
practice interviews and recruitment committee runs."""

from datetime import date, datetime
from typing import Any, Literal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

# Types shared with `app.agents`, which cannot import a feature (contract 6).
# « À postuler » … « Retirée » (SPEC 6.1), in this order.
ApplicationStatus = Literal[
    "to_apply",
    "applied",
    "followed_up",
    "interview",
    "offer",
    "rejected",
    "no_answer",
    "withdrawn",
]
Channel = Literal["company_site", "job_board", "linkedin", "email", "referral", "other"]
EventKind = Literal[
    "created", "status", "note", "reminder", "kit", "interview", "committee", "version"
]
ReminderKind = Literal["linkedin_7", "email_14", "close_21", "thanks", "news_7"]
ReminderStatus = Literal["pending", "done", "ignored"]
KitKind = Literal["cv", "letter", "linkedin", "followups", "form_answers", "company_brief", "pitch"]
KitStatus = Literal["pending", "ready", "to_check", "failed"]
InterviewMode = Literal["behavioral", "technical", "case", "mixed", "salary"]
RunStatus = Literal["running", "done", "failed", "stopped"]
# An interview: `stopped` (stopped before any answer), `debrief_failed` (answers kept, debrief
# not written), `failed` (session closed without a result, set on read).
InterviewStatus = Literal["running", "done", "failed", "stopped", "debrief_failed"]


def _application_fk() -> Mapped[str]:
    return mapped_column(String(36), ForeignKey("applications.id", ondelete="CASCADE"), index=True)


class Application(UserScopedMixin, Base):
    """The record of an application. `posting_id` has no foreign key (like
    `cv_versions.posting_id`):
    the record keeps its frozen copy of the offer text (`posting_text`).
    `distinct_from`: the records confirmed as « autre poste », recorded both ways."""

    __tablename__ = "applications"
    __table_args__ = (
        Index("ix_applications_url", "user_id", "url_norm"),
        Index("ix_applications_company", "user_id", "company_norm"),
        Index("ix_applications_posting", "user_id", "posting_id"),
    )

    posting_id: Mapped[str | None] = mapped_column(String(36), default=None)
    company: Mapped[str] = mapped_column(String(200))
    company_norm: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(200))
    url: Mapped[str | None] = mapped_column(Text, default=None)
    url_norm: Mapped[str | None] = mapped_column(String(2048), default=None)
    posting_text: Mapped[str | None] = mapped_column(Text, default=None)
    channel: Mapped[str | None] = mapped_column(String(16), default=None)
    status: Mapped[str] = mapped_column(String(16), default="to_apply")
    applied_on: Mapped[date | None] = mapped_column(Date, default=None)
    interview_on: Mapped[date | None] = mapped_column(Date, default=None)
    answered_on: Mapped[date | None] = mapped_column(Date, default=None)  # first answer
    cv_version_id: Mapped[str | None] = mapped_column(String(36), default=None)
    letter: Mapped[str | None] = mapped_column(Text, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    next_action: Mapped[str | None] = mapped_column(String(200), default=None)
    next_action_on: Mapped[date | None] = mapped_column(Date, default=None)
    distinct_from: Mapped[list[Any]] = mapped_column(default=list)


class ApplicationEvent(UserScopedMixin, Base):
    """One line of a record's chronological thread."""

    __tablename__ = "application_events"

    application_id: Mapped[str] = _application_fk()
    kind: Mapped[str] = mapped_column(String(16))
    at: Mapped[datetime] = mapped_column(UTCDateTime)
    status_from: Mapped[str | None] = mapped_column(String(16), default=None)
    status_to: Mapped[str | None] = mapped_column(String(16), default=None)
    text: Mapped[str | None] = mapped_column(Text, default=None)
    ref_id: Mapped[str | None] = mapped_column(String(36), default=None)


class Contact(UserScopedMixin, Base):
    """A contact of a record (recruiter, hiring manager)."""

    __tablename__ = "contacts"

    application_id: Mapped[str] = _application_fk()
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str | None] = mapped_column(String(120), default=None)
    url: Mapped[str | None] = mapped_column(String(500), default=None)


class Reminder(UserScopedMixin, Base):
    """A follow-up: never two of the same type for the same anchor (`anchor_on`: the application
    or interview date it derives from)."""

    __tablename__ = "reminders"
    # `uq_reminders_application_id` : (application_id, kind, anchor_on).
    __table_args__ = (
        UniqueConstraint("application_id", "kind", "anchor_on"),
        Index("ix_reminders_due_on_status", "due_on", "status"),
    )

    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(16))
    anchor_on: Mapped[date] = mapped_column(Date)
    due_on: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    done_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    # Postponed by January (« Reporter de 3 jours »): no longer follows the settings' deadlines.
    postponed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")


class KitItem(UserScopedMixin, Base):
    """A piece of the application kit (CV, letter, LinkedIn message...); `meta`: flags,
    sources, word count, language. `edited`: January edited it by hand."""

    __tablename__ = "kit_items"
    # `uq_kit_items_application_id` : (application_id, kind).
    __table_args__ = (UniqueConstraint("application_id", "kind"),)

    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    content: Mapped[str] = mapped_column(Text, default="")
    meta: Mapped[dict[str, Any]] = mapped_column(default=dict)
    edited: Mapped[bool] = mapped_column(Boolean, default=False)
    session_id: Mapped[str | None] = mapped_column(String(36), default=None)


class Interview(UserScopedMixin, Base):
    """A practice interview. `application_id` and `posting_id` have no foreign key:
    an interview outlives the record (or takes place without it)."""

    __tablename__ = "interviews"
    __table_args__ = (Index("ix_interviews_application", "user_id", "application_id"),)

    application_id: Mapped[str | None] = mapped_column(String(36), default=None)
    posting_id: Mapped[str | None] = mapped_column(String(36), default=None)
    role: Mapped[str | None] = mapped_column(String(200), default=None)
    mode: Mapped[str] = mapped_column(String(16))
    duration_min: Mapped[int] = mapped_column(Integer)  # 15, 30 or 45
    language: Mapped[str] = mapped_column(String(2))  # « fr » or « en »
    salary: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    surprise_invitation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("surprise_interview_invitations.id", ondelete="RESTRICT")
    )
    system_design: Mapped[dict[str, Any] | None] = mapped_column(JSON(none_as_null=True))
    session_id: Mapped[str] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(16), default="running")
    exchanges: Mapped[list[Any]] = mapped_column(default=list)
    debrief: Mapped[dict[str, Any] | None] = mapped_column(default=None)


class CommitteeRun(UserScopedMixin, Base):
    """A recruitment committee run on a CV version; `previous_id`: the previous one, to compare."""

    __tablename__ = "committee_runs"
    __table_args__ = (Index("ix_committee_runs_cv_version", "user_id", "cv_version_id"),)

    cv_version_id: Mapped[str] = mapped_column(String(36))
    posting_id: Mapped[str] = mapped_column(String(36))
    application_id: Mapped[str | None] = mapped_column(String(36), default=None)
    session_id: Mapped[str] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(16), default="running")
    votes: Mapped[list[Any]] = mapped_column(default=list)
    verdict: Mapped[str | None] = mapped_column(String(40), default=None)
    objections: Mapped[list[Any]] = mapped_column(default=list)
    changes: Mapped[list[Any]] = mapped_column(default=list)
    previous_id: Mapped[str | None] = mapped_column(String(36), default=None)
