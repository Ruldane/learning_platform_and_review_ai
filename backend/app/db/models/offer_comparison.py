"""Préférences propres au compte et résultats figés des comparaisons."""

from typing import Any

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped

from app.db.base import Base, UserScopedMixin


class OfferComparisonPreference(Base, UserScopedMixin):
    __tablename__ = "offer_comparison_preferences"
    __table_args__ = (UniqueConstraint("user_id"),)

    preferences: Mapped[dict[str, Any]]


class OfferComparisonScenario(Base, UserScopedMixin):
    __tablename__ = "offer_comparisons"

    result: Mapped[dict[str, Any]]
