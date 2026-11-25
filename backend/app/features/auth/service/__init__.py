import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.accounts import User
from app.features.auth.repository import UserRepository

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._users = UserRepository(session)

    async def ensure_local_user(self) -> User:
        """Returns the local user, creating it on the first call (idempotent). If the space has
        been taken over by a Google account (the `local` row then carries an identity) and
        `users` has only one account, that is the single user: switching back to local mode
        gives the data back (review 9.R, A-I1). With several accounts, a new space is created."""
        user = await self._users.get_local() or await self._users.only_user()
        if user is None:
            user = await self._users.add_local()
            if await self._users.any_google_user():
                logger.info("local space taken over by a Google account: new local space")
        return user

    async def get_user(self, user_id: str) -> User:
        user = await self._users.get(user_id)
        if user is None:
            raise AppError("user_not_found", "User not found.", 404)
        return user
