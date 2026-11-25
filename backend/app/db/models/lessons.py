from typing import Any, Literal

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin

# Types shared with `app.agents`, which cannot import a feature (contract 6).
LessonStatus = Literal["pending", "generating", "ready", "failed"]
ResourceType = Literal["documentation", "course", "video", "article", "repository", "paper"]
ResourceLevel = Literal["beginner", "intermediate", "advanced"]
ResourceStatus = Literal["to_read", "read"]
# Production attempts of a lesson (the first and two retries): re-read by the production and by
# the API schema (`LessonSummaryOut.attempts`).
MAX_LESSON_ATTEMPTS = 3


class Lesson(UserScopedMixin, Base):
    """The lesson of a module (only one: `module_id` is unique), in Markdown (SPEC 3.5).

    `attempts` caps the retries of a failed lesson; `report` is the Verifier's report."""

    __tablename__ = "lessons"

    module_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("modules.id", ondelete="CASCADE"), unique=True
    )
    program_id: Mapped[str] = mapped_column(String(36))
    title: Mapped[str] = mapped_column(String(200))
    markdown: Mapped[str] = mapped_column(Text, default="")
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    pdf_key: Mapped[str | None] = mapped_column(
        String(200), default=None, info={"undo_pending_attachment": True}
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    failure_reason: Mapped[str | None] = mapped_column(String(300), default=None)
    session_id: Mapped[str | None] = mapped_column(
        String(36), default=None, info={"undo_publication_session": True}
    )
    report: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    verification_session_id: Mapped[str | None] = mapped_column(
        String(36), default=None, info={"undo_pending_session": True}
    )
    verification_failure_reason: Mapped[str | None] = mapped_column(String(300), default=None)
    # Remarks from the last rejected check (justified notes, unsourced claims): D308.
    verification_feedback: Mapped[list[str] | None] = mapped_column(JSON, default=None)
    verification_draft: Mapped[dict[str, Any] | None] = mapped_column(default=None)


class Resource(UserScopedMixin, Base):
    """A resource of a module (SPEC 3.6); `note` is the reading note."""

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
