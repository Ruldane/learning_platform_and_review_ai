from sqlalchemy import select, text

from app.db.models.meeting_modules import MeetingModule
from app.db.repository import UserScopedRepository


class MeetingModules(UserScopedRepository[MeetingModule]):
    model = MeetingModule

    async def begin_write(self) -> None:
        await self.session.execute(text("BEGIN IMMEDIATE"))

    async def recent(self) -> list[MeetingModule]:
        query = (
            select(self.model)
            .where(self.model.user_id == self.user_id)
            .order_by(self.model.created_at.desc(), self.model.id.desc())
            .limit(50)
        )
        return list(await self.session.scalars(query))
