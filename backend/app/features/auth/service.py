from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.accounts import User
from app.features.auth.repository import UserRepository


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._users = UserRepository(session)

    async def ensure_local_user(self) -> User:
        """Renvoie l'utilisateur local, en le créant au premier appel (idempotent)."""
        return await self._users.get_local() or await self._users.add_local()

    async def get_user(self, user_id: str) -> User:
        user = await self._users.get(user_id)
        if user is None:
            raise AppError("user_not_found", "Utilisateur introuvable.", 404)
        return user
