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
        """Renvoie l'utilisateur local, en le créant au premier appel (idempotent). Si l'espace a
        été repris par un compte Google (la ligne `local` porte alors une identité) et que
        `users` n'a qu'un seul compte, c'est lui l'utilisateur unique : repasser en mode local
        rend les données (revue 9.R, A-I1). Avec plusieurs comptes, un espace neuf est créé."""
        user = await self._users.get_local() or await self._users.only_user()
        if user is None:
            user = await self._users.add_local()
            if await self._users.any_google_user():
                logger.info("espace local repris par un compte Google : nouvel espace local")
        return user

    async def get_user(self, user_id: str) -> User:
        user = await self._users.get(user_id)
        if user is None:
            raise AppError("user_not_found", "Utilisateur introuvable.", 404)
        return user
