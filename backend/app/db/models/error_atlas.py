"""Personal hypotheses and snapshots of the errors that support them."""

from typing import Any

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin


class AtlasHypothesis(UserScopedMixin, Base):
    __tablename__ = "atlas_hypotheses"
    __table_args__ = (UniqueConstraint("user_id", "label_key"),)

    label: Mapped[str] = mapped_column(String(120))
    label_key: Mapped[str] = mapped_column(String(64))
    exercise: Mapped[dict[str, Any] | None]


class AtlasObservation(UserScopedMixin, Base):
    __tablename__ = "atlas_observations"
    __table_args__ = (UniqueConstraint("user_id", "hypothesis_id", "evidence_key"),)

    hypothesis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("atlas_hypotheses.id", ondelete="CASCADE")
    )
    evidence_key: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[str] = mapped_column(String(8))
    evidence: Mapped[dict[str, Any]]
