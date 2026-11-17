"""Qui est l'utilisateur de la requête (P7) : l'utilisateur unique en mode local, le cookie de
session en mode Google. Toute anomalie (cookie absent, falsifié, expiré, utilisateur supprimé,
adresse retirée de `ALLOWED_EMAILS`) donne la même 401 `auth_required`, jamais un autre compte."""

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.requests import HTTPConnection

from app.config import Settings
from app.core.deps import Authenticator, CurrentUser
from app.core.errors import AppError
from app.features.auth.repository import UserRepository
from app.features.auth.repository_sessions import AuthSessionRepository
from app.features.auth.service.allowlist import allowed
from app.features.auth.service.cookies import SESSION_COOKIE
from app.features.auth.service.sessions import hash_token


def _auth_required() -> AppError:
    return AppError("auth_required", "Connexion requise.", 401)


class LocalAuthenticator:
    """Mode local : toute requête est celle de l'utilisateur unique créé au démarrage."""

    def __init__(self, user_id: str) -> None:
        self._user_id = user_id

    async def authenticate(self, conn: HTTPConnection) -> CurrentUser:
        return CurrentUser(id=self._user_id, email=None)


class CookieAuthenticator:
    """Mode Google : cookie `tremplin_session` → SHA-256 → session non expirée → utilisateur →
    adresse toujours autorisée. Une session courte et en lecture seule par requête."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        now: Callable[[], datetime],
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._now = now

    async def authenticate(self, conn: HTTPConnection) -> CurrentUser:
        token = conn.cookies.get(SESSION_COOKIE)
        if not token:
            raise _auth_required()
        async with self._session_factory() as db:
            session = await AuthSessionRepository(db).get_valid(hash_token(token), self._now())
            user = await UserRepository(db).get(session.user_id) if session else None
        # La lecture de `allowed_emails` est faite ici, à chaque requête (pas à la construction).
        if user is None or not user.email or not allowed(user.email, self._settings.allowed_emails):
            raise _auth_required()
        return CurrentUser(id=user.id, email=user.email)


def build_authenticator(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    local_user_id: str | None,
) -> Authenticator:
    if settings.auth_mode == "local":
        if local_user_id is None:
            raise RuntimeError("Mode local : l'utilisateur local n'existe pas encore.")
        return LocalAuthenticator(local_user_id)
    return CookieAuthenticator(session_factory, settings, lambda: datetime.now(UTC))
