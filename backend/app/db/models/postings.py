"""Offres d'emploi et fiches d'entreprise (phase 6, D118) : la copie figée du texte d'une offre,
son analyse, ses doublons et l'écart de compétences calculé contre elle."""

from datetime import datetime
from typing import Any, Literal, TypedDict

from sqlalchemy import Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

# Types partagés avec `app.agents`, qui ne peut pas importer une feature (contrat 6).
PostingStatus = Literal["analyzing", "ready", "rejected", "failed"]
PostingSource = Literal["url", "text"]


class GapMatch(TypedDict):
    """Un besoin de l'offre (`SkillNeed.name`) rattaché à une compétence connue du référentiel
    de January (son nom), ou à rien (`None`)."""

    need: str
    known: str | None


class GapResult(TypedDict):
    """Forme JSON de `job_postings.gap` (preflight G25) : les rattachements de la session
    `gap_analysis` qui les a produits. Les lignes de l'écart sont recalculées à la lecture."""

    session_id: str
    matches: list[GapMatch]


class JobPosting(UserScopedMixin, Base):
    """Une offre ajoutée par January, par lien ou par texte collé. `text` est la copie figée lue
    à l'ajout ; un même lien (`url_norm`) ou un même texte collé (`text_hash`) ne fait qu'une
    offre par utilisateur (index uniques partiels : idempotence de `POST /postings`)."""

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
    """La fiche d'une entreprise, partagée par les offres et les revues de CV ; `name_norm`
    (`company_key`) la dédoublonne."""

    __tablename__ = "companies"
    # `uq_companies_user_id` : (user_id, name_norm).
    __table_args__ = (UniqueConstraint("user_id", "name_norm"),)

    name: Mapped[str] = mapped_column(String(200))
    name_norm: Mapped[str] = mapped_column(String(200))
    brief: Mapped[dict[str, Any] | None] = mapped_column(default=None)  # CompanyBrief (6.12)
    sources: Mapped[list[Any]] = mapped_column(default=list)
    ats: Mapped[str | None] = mapped_column(String(40), default=None)
    refreshed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
