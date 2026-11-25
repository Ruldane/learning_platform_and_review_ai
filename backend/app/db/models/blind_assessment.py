"""Test of frozen texts and secret assignment of the letters A and B."""

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

BlindStage = Literal["draft", "evaluating", "complete"]


class BlindAssessment(Base, UserScopedMixin):
    __tablename__ = "blind_assessments"

    rubric: Mapped[dict[str, Any]]
    # Composing the account archive does not reveal a draw in progress.
    source_a: Mapped[dict[str, Any]] = mapped_column(info={"export": False})
    source_b: Mapped[dict[str, Any]] = mapped_column(info={"export": False})
    stage: Mapped[BlindStage] = mapped_column(String(12), default="draft")
    session_id: Mapped[str | None] = mapped_column(String(36))
    grade: Mapped[dict[str, Any] | None]
    evaluated_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
