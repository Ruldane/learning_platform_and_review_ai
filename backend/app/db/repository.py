import builtins
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import UserScopedMixin

# Champs que l'appelant ne peut jamais imposer : ils appartiennent au repository.
_PROTECTED_ON_UPDATE = {"id", "user_id", "created_at"}


class UserScopedRepository[M: UserScopedMixin]:
    """Accès aux lignes d'un seul utilisateur : `user_id` est imposé à l'insertion
    et ajouté à chaque `WHERE`. Les sous-classes fixent l'attribut `model`.

    Les écritures font un `flush` ; le commit appartient à la session de la requête (`get_db`).
    """

    model: type[M]

    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self.session = session
        self.user_id = user_id

    async def get(self, id: str) -> M | None:
        stmt = select(self.model).where(self.model.id == id, self.model.user_id == self.user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def add(self, **fields: Any) -> M:
        row = self.model(**{**fields, "user_id": self.user_id})
        self.session.add(row)
        await self.session.flush()
        return row

    async def update(self, id: str, **fields: Any) -> M | None:
        row = await self.get(id)
        if row is None:
            return None
        for key, value in fields.items():
            if key not in _PROTECTED_ON_UPDATE:
                setattr(row, key, value)
        await self.session.flush()
        return row

    async def delete(self, id: str) -> bool:
        row = await self.get(id)
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True

    async def list(self, **filters: Any) -> builtins.list[M]:
        stmt = select(self.model).where(self.model.user_id == self.user_id)
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        return builtins.list((await self.session.execute(stmt)).scalars().all())
