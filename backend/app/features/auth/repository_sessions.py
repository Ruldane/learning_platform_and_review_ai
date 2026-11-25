from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.accounts import AuthSession


class AuthSessionRepository:
    """Access to the `auth_sessions` table.

    Documented exception to filtering by `user_id` (DECISIONS D23): a session is looked up by
    the SHA-256 of its token (`token_hash`), because the query does not yet know who the user
    is; the session itself says so. The token itself is never kept.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user_id: str, token_hash: str, expires_at: datetime) -> AuthSession:
        row = AuthSession(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_valid(self, token_hash: str, now: datetime) -> AuthSession | None:
        """The session for this token if it has not expired (comparison done here, in UTC)."""
        stmt = select(AuthSession).where(AuthSession.token_hash == token_hash)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return row if row is not None and row.expires_at > now else None

    async def delete(self, token_hash: str) -> None:
        await self._session.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash))

    async def purge_expired(self, user_id: str, now: datetime) -> None:
        """Removes this user's expired sessions (the others' are left alone)."""
        stmt = delete(AuthSession).where(
            AuthSession.user_id == user_id, AuthSession.expires_at <= now
        )
        await self._session.execute(stmt)
