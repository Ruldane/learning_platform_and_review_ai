from sqlalchemy import select, text

from app.db.models.contradictory_watch import WatchExperiment
from app.db.repository import UserScopedRepository


class WatchRepository(UserScopedRepository[WatchExperiment]):
    model = WatchExperiment

    async def recent(self) -> list[WatchExperiment]:
        statement = (
            select(self.model)
            .where(self.model.user_id == self.user_id)
            .order_by(self.model.created_at.desc(), self.model.id.desc())
            .limit(100)
        )
        return list(await self.session.scalars(statement))

    async def begin_write(self) -> None:
        await self.session.execute(text("BEGIN IMMEDIATE"))
