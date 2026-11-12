from typing import Any, Literal

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin

# Types partagés avec `app.agents`, qui ne peut pas importer une feature (contrat 6).
LessonStatus = Literal["pending", "generating", "ready", "failed"]
ResourceType = Literal["documentation", "cours", "video", "article", "depot", "papier"]
ResourceLevel = Literal["debutant", "intermediaire", "avance"]
ResourceStatus = Literal["to_read", "read"]
# Essais de production d'une leçon (le premier et deux relances) : relu par la production et par
# le schéma de l'API (`LessonSummaryOut.attempts`).
MAX_LESSON_ATTEMPTS = 3


class Lesson(UserScopedMixin, Base):
    """La leçon d'un module (une seule : `module_id` est unique), en Markdown (SPEC 3.5).

    `attempts` borne les relances d'une leçon en échec ; `report` est le rapport du Vérificateur.
    """

    __tablename__ = "lessons"

    module_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("modules.id", ondelete="CASCADE"), unique=True
    )
    program_id: Mapped[str] = mapped_column(String(36))
    title: Mapped[str] = mapped_column(String(200))
    markdown: Mapped[str] = mapped_column(Text, default="")
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    pdf_key: Mapped[str | None] = mapped_column(String(200), default=None)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    failure_reason: Mapped[str | None] = mapped_column(String(300), default=None)
    session_id: Mapped[str | None] = mapped_column(String(36), default=None)
    report: Mapped[dict[str, Any] | None] = mapped_column(default=None)


class Resource(UserScopedMixin, Base):
    """Une ressource d'un module (SPEC 3.6) ; `note` est la fiche de lecture."""

    __tablename__ = "resources"
    # `uq_resources_module_id` : (module_id, url_hash).
    __table_args__ = (
        UniqueConstraint("module_id", "url_hash"),
        Index("ix_resources_user_program", "user_id", "program_id"),
    )

    module_id: Mapped[str] = mapped_column(String(36), ForeignKey("modules.id", ondelete="CASCADE"))
    program_id: Mapped[str] = mapped_column(String(36))
    source_id: Mapped[str | None] = mapped_column(String(36), default=None)
    type: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    url_hash: Mapped[str] = mapped_column(String(64))
    author: Mapped[str | None] = mapped_column(Text, default=None)
    published: Mapped[str | None] = mapped_column(String(32), default=None)
    lang: Mapped[str | None] = mapped_column(String(8), default=None)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, default=None)
    level: Mapped[str | None] = mapped_column(String(16), default=None)
    reason: Mapped[str] = mapped_column(String(300), default="")
    score: Mapped[int | None] = mapped_column(Integer, default=None)
    local_key: Mapped[str | None] = mapped_column(String(200), default=None)
    note: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(8), default="to_read")
