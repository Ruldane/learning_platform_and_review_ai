"""First reading, submission, second reading and decision, kept separately."""

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

AppealDecision = Literal["keep_original", "accept_second"]


class GradeAppeal(Base, UserScopedMixin):
    __tablename__ = "grade_appeals"

    project_id: Mapped[str] = mapped_column(String(36))
    source: Mapped[dict[str, Any]]
    reason: Mapped[str] = mapped_column(Text)
    session_id: Mapped[str | None] = mapped_column(String(36))
    second: Mapped[dict[str, Any] | None]
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    decision: Mapped[AppealDecision | None] = mapped_column(String(20))
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
