"""Sign-in sessions (P6): random token of 32 bytes, only its SHA-256 is kept, fixed duration
from sign-in (not sliding). No token is logged."""

import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.repository_sessions import AuthSessionRepository


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def open_session(db: AsyncSession, user_id: str, *, now: datetime, days: int) -> str:
    """Opens a session and returns its token (to set as a cookie); first removes the expired
    sessions of this user."""
    sessions = AuthSessionRepository(db)
    await sessions.purge_expired(user_id, now)
    token = secrets.token_urlsafe(32)
    await sessions.add(user_id, hash_token(token), now + timedelta(days=days))
    return token


async def close_session(db: AsyncSession, token: str) -> None:
    """Removes the session for this token; no effect if it does not exist."""
    await AuthSessionRepository(db).delete(hash_token(token))
