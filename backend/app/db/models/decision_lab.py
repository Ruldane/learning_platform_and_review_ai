from typing import Any

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin


class DecisionScenario(UserScopedMixin, Base):
    __tablename__ = "decision_lab_scenarios"

    title: Mapped[str] = mapped_column(String(120))
    assumptions: Mapped[dict[str, Any]]
    results: Mapped[dict[str, Any]]
    critique: Mapped[str] = mapped_column(Text)
