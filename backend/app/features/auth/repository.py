from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_id
from app.db.models.accounts import User

LOCAL_USER_NAME = "local"


class UserRepository:
    """Accès à la table `users`.

    Exception documentée au filtrage par `user_id` (DECISIONS D23) : c'est la table des comptes,
    on y filtre par `id`. N'hérite donc pas de `UserScopedRepository`.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: str) -> User | None:
        return await self._session.get(User, user_id)

    async def get_local(self) -> User | None:
        """Compte local : sans e-mail ni identifiant Google, nommé `local`."""
        stmt = select(User).where(
            User.name == LOCAL_USER_NAME, User.email.is_(None), User.google_sub.is_(None)
        )
        return (await self._session.execute(stmt.limit(1))).scalar_one_or_none()

    async def add_local(self) -> User:
        user_id = new_id()
        user = User(id=user_id, user_id=user_id, name=LOCAL_USER_NAME)  # convention user_id == id
        self._session.add(user)
        await self._session.flush()
        return user

    async def get_by_google_sub(self, sub: str) -> User | None:
        stmt = select(User).where(User.google_sub == sub)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add_google(self, *, sub: str, email: str, name: str) -> User:
        user_id = new_id()
        user = User(id=user_id, user_id=user_id, google_sub=sub, email=email, name=name)
        self._session.add(user)
        await self._session.flush()
        return user

    async def update_identity(self, user: User, *, email: str, name: str) -> None:
        user.email = email
        user.name = name
        await self._session.flush()
