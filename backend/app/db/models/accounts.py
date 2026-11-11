from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime


class User(UserScopedMixin, Base):
    """Compte utilisateur. Par convention `user_id == id` (à fixer à la création)."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    google_sub: Mapped[str | None] = mapped_column(String(64), unique=True, default=None)
    language: Mapped[str] = mapped_column(String(8), default="fr")


class UserSettingsRow(UserScopedMixin, Base):
    """Réglages d'un utilisateur : une seule ligne par utilisateur."""

    __tablename__ = "user_settings"
    __table_args__ = (UniqueConstraint("user_id"),)

    data: Mapped[dict[str, Any]] = mapped_column(default=dict)


class ApiKey(UserScopedMixin, Base):
    """Clé API d'un fournisseur, chiffrée ; seuls les 4 derniers caractères sont lisibles."""

    __tablename__ = "api_keys"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_api_keys_user_id_provider"),)

    provider: Mapped[str] = mapped_column(String(32))
    encrypted_key: Mapped[str] = mapped_column(Text)
    last4: Mapped[str] = mapped_column(String(4))
    last_tested_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    last_test_ok: Mapped[bool | None] = mapped_column(Boolean, default=None)
