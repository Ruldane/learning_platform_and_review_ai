"""Job offers and company records (phase 6, D118): the frozen copy of an offer's text, its
analysis, its duplicates and the skill gap computed against it."""

from datetime import datetime
from typing import Any, Literal, TypedDict

from sqlalchemy import Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

# Types shared with `app.agents`, which cannot import a feature (contract 6).
PostingStatus = Literal["analyzing", "ready", "rejected", "failed"]
PostingSource = Literal["url", "text"]


class GapMatch(TypedDict):
    """A need of the offer (`SkillNeed.name`) linked to a skill known in January's catalog (its
    name), or to nothing (`None`)."""

    need: str
    known: str | None


class GapResult(TypedDict):
    """JSON shape of `job_postings.gap` (preflight G25): the links from the `gap_analysis` session
    that produced them. The gap rows are recomputed on read."""

    session_id: str
    matches: list[GapMatch]


class JobPosting(UserScopedMixin, Base):
    """An offer added by January, by link or pasted text. `text` is the frozen copy read at
    addition;
    the same link (`url_norm`) or the same pasted text (`text_hash`) makes only one offer per
    user (partial unique indexes: idempotence of `POST /postings`)."""

    __tablename__ = "job_postings"
    __table_args__ = (
        Index(
            "uq_job_postings_url",
            "user_id",
            "url_norm",
            unique=True,
            sqlite_where=text("url_norm IS NOT NULL"),
        ),
        Index(
            "uq_job_postings_text",
            "user_id",
            "text_hash",
            unique=True,
            sqlite_where=text("url_norm IS NULL"),
        ),
        Index("ix_job_postings_company_title", "user_id", "company_norm", "title"),
    )

    url: Mapped[str | None] = mapped_column(Text, default=None)
    url_norm: Mapped[str | None] = mapped_column(String(2048), default=None)
    source: Mapped[str] = mapped_column(String(8))
    company: Mapped[str | None] = mapped_column(String(200), default=None)
    company_norm: Mapped[str | None] = mapped_column(String(200), default=None)
    title: Mapped[str | None] = mapped_column(String(200), default=None)
    text: Mapped[str] = mapped_column(Text)
    text_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(12), default="analyzing")
    analysis: Mapped[dict[str, Any] | None] = mapped_column(default=None)  # PostingAnalysis
    duplicates: Mapped[list[Any]] = mapped_column(default=list)  # DuplicateHit (6.5)
    distinct_from: Mapped[list[Any]] = mapped_column(default=list)
    memory_item_id: Mapped[str | None] = mapped_column(String(36), default=None)
    gap: Mapped[dict[str, Any] | None] = mapped_column(default=None)  # GapResult
    gap_session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    failure_reason: Mapped[str | None] = mapped_column(String(300), default=None)


class Company(UserScopedMixin, Base):
    """The record of a company, shared by offers and CV reviews; `name_norm` (`company_key`)
    de-duplicates it."""

    __tablename__ = "companies"
    # `uq_companies_user_id` : (user_id, name_norm).
    __table_args__ = (UniqueConstraint("user_id", "name_norm"),)

    name: Mapped[str] = mapped_column(String(200))
    name_norm: Mapped[str] = mapped_column(String(200))
    brief: Mapped[dict[str, Any] | None] = mapped_column(default=None)  # CompanyBrief (6.12)
    sources: Mapped[list[Any]] = mapped_column(default=list)
    ats: Mapped[str | None] = mapped_column(String(40), default=None)
    refreshed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    # Company briefing file (phase 7): content, sources read, reading date.
    dossier: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    dossier_sources: Mapped[list[Any]] = mapped_column(default=list)
    dossier_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
