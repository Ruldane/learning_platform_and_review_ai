from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin


class Contribution(UserScopedMixin, Base):
    __tablename__ = "contributions"
    __table_args__ = (UniqueConstraint("user_id", "repository", "issue_number"),)

    program_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("programs.id", ondelete="CASCADE")
    )
    chapter_id: Mapped[str] = mapped_column(String(36))
    chapter_title: Mapped[str] = mapped_column(String(200))
    repository: Mapped[str] = mapped_column(String(140))
    issue_number: Mapped[int] = mapped_column(Integer)
    issue_title: Mapped[str] = mapped_column(String(200))
    issue_body: Mapped[str] = mapped_column(Text)
    skills: Mapped[list[Any]] = mapped_column()
    base: Mapped[str] = mapped_column(String(100))
    marker: Mapped[str] = mapped_column(String(36), info={"export": False})
    publication: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(String(12), default="draft")
    pull_number: Mapped[int | None] = mapped_column(Integer, default=None)
    revision: Mapped[int] = mapped_column(Integer, default=0)
