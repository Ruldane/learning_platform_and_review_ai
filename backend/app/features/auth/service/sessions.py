"""Sessions de connexion (P6) : jeton aléatoire de 32 octets, seul son SHA-256 est gardé, durée
fixe depuis la connexion (pas glissante). Aucun jeton n'est journalisé."""

import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.repository_sessions import AuthSessionRepository


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def open_session(db: AsyncSession, user_id: str, *, now: datetime, days: int) -> str:
    """Ouvre une session et rend son jeton (à poser en cookie) ; retire d'abord les sessions
    expirées de cette utilisatrice."""
    sessions = AuthSessionRepository(db)
    await sessions.purge_expired(user_id, now)
    token = secrets.token_urlsafe(32)
    await sessions.add(user_id, hash_token(token), now + timedelta(days=days))
    return token


async def close_session(db: AsyncSession, token: str) -> None:
    """Retire la session de ce jeton ; sans effet si elle n'existe pas."""
    await AuthSessionRepository(db).delete(hash_token(token))
