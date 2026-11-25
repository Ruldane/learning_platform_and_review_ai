from sqlalchemy import select, update

from app.db.models.lab import LabPreferencesRow
from app.db.repository import UserScopedRepository


class LabPreferencesRepository(UserScopedRepository[LabPreferencesRow]):
    model = LabPreferencesRow

    async def read(self) -> LabPreferencesRow | None:
        stmt = select(self.model).where(self.model.user_id == self.user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def locked(self) -> LabPreferencesRow | None:
        # Start the SQLite write before the read to serialize the two PATCH fields.
        stmt = update(self.model).where(self.model.user_id == self.user_id, self.model.id == "")
        await self.session.execute(stmt.values(updated_at=self.model.updated_at))
        return await self.read()
