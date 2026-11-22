from sqlalchemy import select, text

from app.db.models.incident_replay import IncidentReplay
from app.db.repository import UserScopedRepository


class IncidentReplays(UserScopedRepository[IncidentReplay]):
    model = IncidentReplay

    async def begin_write(self) -> None:
        await self.session.execute(text("BEGIN IMMEDIATE"))

    async def by_receipt(self, receipt: str) -> IncidentReplay | None:
        return await self.session.scalar(
            select(self.model).where(
                self.model.user_id == self.user_id, self.model.receipt == receipt
            )
        )

    async def recent(self) -> list[IncidentReplay]:
        query = (
            select(self.model)
            .where(self.model.user_id == self.user_id)
            .order_by(self.model.created_at.desc(), self.model.id.desc())
            .limit(50)
        )
        return list(await self.session.scalars(query))
