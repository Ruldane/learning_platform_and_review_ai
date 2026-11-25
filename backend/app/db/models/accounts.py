from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

# Reserved settings key of the `local` user: resuming the local space is closed
# (a first Google account has existed). Outside the rows that « Tout supprimer » erases for an
# Google account; never exposed by the settings API.
LOCAL_CLAIM_CLOSED = "local_claim_closed"


class User(UserScopedMixin, Base):
    """User account. By convention `user_id == id` (to be set at creation)."""

    __tablename__ = "users"

    email: Mapped[str | None] = mapped_column(String(320), unique=True, default=None)
    name: Mapped[str] = mapped_column(String(200), default="")
    google_sub: Mapped[str | None] = mapped_column(String(64), unique=True, default=None)
    language: Mapped[str] = mapped_column(String(8), default="en")


class UserSettingsRow(UserScopedMixin, Base):
    """A user's settings: a single row per user."""

    __tablename__ = "user_settings"
    __table_args__ = (UniqueConstraint("user_id"),)

    data: Mapped[dict[str, Any]] = mapped_column(default=dict)


class ApiKey(UserScopedMixin, Base):
    """API key of a provider, encrypted; only the last 4 characters are readable."""

    __tablename__ = "api_keys"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_api_keys_user_id_provider"),)

    provider: Mapped[str] = mapped_column(String(32))
    encrypted_key: Mapped[str] = mapped_column(Text, info={"export": False})  # never exported
    last4: Mapped[str] = mapped_column(String(4))
    last_tested_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    last_test_ok: Mapped[bool | None] = mapped_column(Boolean, default=None)


class AuthSession(UserScopedMixin, Base):
    """Sign-in session of the Google mode (9.A2): only the SHA-256 of the cookie token is kept
    (never the token); the session is valid until `expires_at` (fixed duration from sign-in)."""

    __tablename__ = "auth_sessions"
    __table_args__ = ({"info": {"export": False}},)  # never exported: a token fingerprint

    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)


class AccountVectorPurge(UserScopedMixin, Base):
    """Final purge of a deleted Google account. Without a reference to the account row."""

    __tablename__ = "account_vector_purges"
    __table_args__ = (UniqueConstraint("user_id"), {"info": {"export": False}})
