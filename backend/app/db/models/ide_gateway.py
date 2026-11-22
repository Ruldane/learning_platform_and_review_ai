"""Réservations journalières de la passerelle de l'IDE, sans contenu des appels."""

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin


class IdeGatewayBudget(UserScopedMixin, Base):
    __tablename__ = "ide_gateway_budgets"
    __table_args__ = (UniqueConstraint("user_id", "day"),)

    day: Mapped[str] = mapped_column(String(10))
    reserved: Mapped[int] = mapped_column(Integer)
