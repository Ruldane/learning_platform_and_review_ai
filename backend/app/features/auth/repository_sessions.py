from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.accounts import AuthSession


class AuthSessionRepository:
    """Accès à la table `auth_sessions`.

    Exception documentée au filtrage par `user_id` (DECISIONS D23) : on retrouve une session par
    le SHA-256 de son jeton (`token_hash`), car la requête ne sait pas encore qui elle est ; c'est
    justement la session qui le dit. Le jeton lui-même n'est jamais gardé.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user_id: str, token_hash: str, expires_at: datetime) -> AuthSession:
        row = AuthSession(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_valid(self, token_hash: str, now: datetime) -> AuthSession | None:
        """La session de ce jeton si elle n'est pas expirée (comparaison faite ici, en UTC)."""
        stmt = select(AuthSession).where(AuthSession.token_hash == token_hash)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return row if row is not None and row.expires_at > now else None

    async def delete(self, token_hash: str) -> None:
        await self._session.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash))

    async def purge_expired(self, user_id: str, now: datetime) -> None:
        """Retire les sessions expirées de cette utilisatrice (celles des autres ne bougent pas)."""
        stmt = delete(AuthSession).where(
            AuthSession.user_id == user_id, AuthSession.expires_at <= now
        )
        await self._session.execute(stmt)
