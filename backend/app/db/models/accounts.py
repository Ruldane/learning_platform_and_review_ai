from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

# Clé réservée des réglages de l'utilisateur `local` : la reprise de l'espace local est close
# (un premier compte Google a existé). Hors des lignes qu'efface « Tout supprimer » d'un compte
# Google ; jamais exposée par l'API des réglages.
LOCAL_CLAIM_CLOSED = "local_claim_closed"


class User(UserScopedMixin, Base):
    """Compte utilisateur. Par convention `user_id == id` (à fixer à la création)."""

    __tablename__ = "users"

    email: Mapped[str | None] = mapped_column(String(320), unique=True, default=None)
    name: Mapped[str] = mapped_column(String(200), default="")
    google_sub: Mapped[str | None] = mapped_column(String(64), unique=True, default=None)
    language: Mapped[str] = mapped_column(String(8), default="en")


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
    encrypted_key: Mapped[str] = mapped_column(Text, info={"export": False})  # jamais exportée
    last4: Mapped[str] = mapped_column(String(4))
    last_tested_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    last_test_ok: Mapped[bool | None] = mapped_column(Boolean, default=None)


class AuthSession(UserScopedMixin, Base):
    """Session de connexion du mode Google (9.A2) : seul le SHA-256 du jeton du cookie est gardé
    (jamais le jeton), la session vaut jusqu'à `expires_at` (durée fixe depuis la connexion)."""

    __tablename__ = "auth_sessions"
    __table_args__ = ({"info": {"export": False}},)  # jamais exportée : une empreinte de jeton

    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)


class AccountVectorPurge(UserScopedMixin, Base):
    """Purge finale d'un compte Google supprimé. Sans référence à la ligne du compte."""

    __tablename__ = "account_vector_purges"
    __table_args__ = (UniqueConstraint("user_id"), {"info": {"export": False}})
