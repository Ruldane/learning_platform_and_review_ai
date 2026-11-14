"""Tables du CV (phase 6, D118) : profil maître versionné, gabarits, revues ciblées, leurs
modifications et les versions de CV produites. Le profil et le CV sont des données personnelles :
seuls leurs identifiants sont journalisés."""

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

# Types partagés avec `app.agents`, qui ne peut pas importer une feature (contrat 6).
ProfileStatus = Literal["draft", "validated"]
ProfileOrigin = Literal["archivist", "january"]
TemplateStatus = Literal["capturing", "review", "ready", "failed", "archived"]
ReviewStatus = Literal["running", "proposed", "done", "failed", "cancelled"]
ModificationStatus = Literal["proposed", "to_confirm", "accepted", "refused"]
VersionStatus = Literal["rendering", "ready", "pages_exceeded", "failed"]


class MasterProfile(UserScopedMixin, Base):
    """Une version du profil maître (`data` : `MasterProfileData`). `dropped` garde le texte des
    lignes retirées du brouillon (chiffre introuvable, texte invisible) : montré à January seule,
    jamais journalisé (preflight G5)."""

    __tablename__ = "master_profile"
    # `uq_master_profile_user_id` : (user_id, version).
    __table_args__ = (UniqueConstraint("user_id", "version"),)

    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(12), default="draft")
    data: Mapped[dict[str, Any]] = mapped_column()
    source: Mapped[str] = mapped_column(String(16))
    session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    document_ids: Mapped[list[Any]] = mapped_column(default=list)
    dropped: Mapped[list[Any]] = mapped_column(default=list)


class CvTemplate(UserScopedMixin, Base):
    """Un gabarit capturé d'un CV d'origine : la description du Maquettiste (`spec`), le HTML et
    le CSS écrits par le code, les polices (`FontUse`) et la ressemblance mesurée. Un seul
    gabarit actif par utilisateur (index unique partiel)."""

    __tablename__ = "cv_templates"
    __table_args__ = (
        Index("uq_cv_templates_active", "user_id", unique=True, sqlite_where=text("active = 1")),
    )

    document_id: Mapped[str] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(12), default="capturing")
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    spec: Mapped[dict[str, Any] | None] = mapped_column(default=None)  # TemplateSpec
    html: Mapped[str | None] = mapped_column(Text, default=None)
    css: Mapped[str | None] = mapped_column(Text, default=None)
    fonts: Mapped[list[Any]] = mapped_column(default=list)  # FontUse
    font_gaps: Mapped[list[Any]] = mapped_column(default=list)
    score: Mapped[int | None] = mapped_column(Integer, default=None)
    score_detail: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    passes: Mapped[int] = mapped_column(Integer, default=0)
    page_count: Mapped[int] = mapped_column(Integer)
    page_size: Mapped[dict[str, Any]] = mapped_column()  # {width_pt, height_pt}
    original_pages: Mapped[list[Any]] = mapped_column(default=list)  # clés de stockage .png
    render_pages: Mapped[list[Any]] = mapped_column(default=list)
    sample_content: Mapped[dict[str, Any] | None] = mapped_column(default=None)  # CvContent
    selectable: Mapped[bool] = mapped_column(Boolean)
    session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    failure_reason: Mapped[str | None] = mapped_column(String(300), default=None)
    # CV d'origine préparé (D126) : géométrie des pages, blocs résumés, texte visible, polices
    # (rôles et fichiers rangés) ; relu tel quel, jamais extrait deux fois.
    prepared: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    # Une entrée par passe rendue : numéro, score, ressemblance, clés des images du rendu.
    pass_log: Mapped[list[Any]] = mapped_column(default=list)


OPEN_REVIEW_STATUSES = ("running", "proposed")  # une revue en cours : session ouverte


class CvReview(UserScopedMixin, Base):
    """La revue d'un CV contre une offre : indicateurs avant et après, rapport, mots clés partis
    vers l'écart (F8)."""

    __tablename__ = "cv_reviews"

    posting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("job_postings.id", ondelete="CASCADE")
    )
    template_id: Mapped[str] = mapped_column(String(36))
    profile_version: Mapped[int] = mapped_column(Integer)
    session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    status: Mapped[str] = mapped_column(String(12), default="running")
    before: Mapped[dict[str, Any] | None] = mapped_column(default=None)  # Indicators
    after: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    report: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    keywords_to_gap: Mapped[list[Any]] = mapped_column(default=list)
    company_id: Mapped[str | None] = mapped_column(String(36), default=None)


class CvModification(UserScopedMixin, Base):
    """Une modification proposée par un agent (`ref` : « m3 »), adossée à des faits du profil ;
    `blocks` dit pourquoi elle est « à confirmer »."""

    __tablename__ = "cv_modifications"
    # `uq_cv_modifications_review_id` : (review_id, ref).
    __table_args__ = (UniqueConstraint("review_id", "ref"),)

    review_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cv_reviews.id", ondelete="CASCADE")
    )
    ref: Mapped[str] = mapped_column(String(8))
    section: Mapped[str] = mapped_column(String(16))
    action: Mapped[str] = mapped_column(String(8))
    target: Mapped[str | None] = mapped_column(String(40), default=None)
    before: Mapped[str] = mapped_column(Text)
    after: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(12))
    fact_ids: Mapped[list[Any]] = mapped_column(default=list)
    status: Mapped[str] = mapped_column(String(12))
    blocks: Mapped[list[Any]] = mapped_column(default=list)
    author: Mapped[str] = mapped_column(String(32))
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)


class CvVersion(UserScopedMixin, Base):
    """Un CV produit pour une offre (`number` compte par offre). `decisions` fige l'état des
    modifications au clic ; `filename` est le nom ASCII `CV_…pdf`, jamais journalisé."""

    __tablename__ = "cv_versions"
    # `uq_cv_versions_posting_id` : (posting_id, number).
    __table_args__ = (
        UniqueConstraint("posting_id", "number"),
        Index("ix_cv_versions_user_review", "user_id", "review_id"),
    )

    review_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cv_reviews.id", ondelete="CASCADE")
    )
    posting_id: Mapped[str] = mapped_column(String(36))
    template_id: Mapped[str] = mapped_column(String(36))
    number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="rendering")
    content: Mapped[dict[str, Any]] = mapped_column()  # CvContent
    decisions: Mapped[dict[str, Any]] = mapped_column(default=dict)  # ref → statut
    storage_key: Mapped[str | None] = mapped_column(String(200), default=None)
    filename: Mapped[str] = mapped_column(String(160))
    page_count: Mapped[int | None] = mapped_column(Integer, default=None)
    original_page_count: Mapped[int] = mapped_column(Integer)
    allow_extra_pages: Mapped[bool] = mapped_column(Boolean, default=False)
    page_images: Mapped[list[Any]] = mapped_column(default=list)
    ats: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    coverage: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    failure_reason: Mapped[str | None] = mapped_column(String(300), default=None)
