from typing import Any

from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin


class LinkedInDraft(UserScopedMixin, Base):
    __tablename__ = "linkedin_drafts"
    __table_args__ = (Index("ix_linkedin_drafts_user_created", "user_id", "created_at"),)

    profile_version: Mapped[int] = mapped_column(Integer)
    posting_id: Mapped[str | None] = mapped_column(String(36), default=None)
    session_id: Mapped[str] = mapped_column(String(36))
    text: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    revision: Mapped[int] = mapped_column(Integer, default=0)
