"""Private result of the reading and Python project created for the experiment."""

from typing import Literal

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin

type PaperStage = Literal["queued", "ready"]


class PaperLab(UserScopedMixin, Base):
    __tablename__ = "paper_labs"

    url: Mapped[str] = mapped_column(String(2083))
    source_title: Mapped[str | None] = mapped_column(String(240))
    title: Mapped[str | None] = mapped_column(String(180))
    course: Mapped[str | None] = mapped_column(Text)
    expected: Mapped[str | None] = mapped_column(Text)
    ide_session_id: Mapped[str | None] = mapped_column(String(36))
    session_id: Mapped[str] = mapped_column(String(36))
    stage: Mapped[PaperStage] = mapped_column(String(8))
