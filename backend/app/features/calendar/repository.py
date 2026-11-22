from datetime import datetime

from sqlalchemy import select, update

from app.db.models.calendar import CalendarConnection, CalendarProposal
from app.db.repository import UserScopedRepository


class Connections(UserScopedRepository[CalendarConnection]):
    model = CalendarConnection

    async def current(self) -> CalendarConnection | None:
        stmt = select(self.model).where(self.model.user_id == self.user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def consume(self, digest: str, now: datetime) -> bool:
        table = self.model
        stmt = (
            update(table)
            .where(
                table.user_id == self.user_id,
                table.oauth_state_hash == digest,
                table.oauth_expires_at > now,
            )
            .values(oauth_state_hash=None, oauth_expires_at=None)
            .returning(table.id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None


class Proposals(UserScopedRepository[CalendarProposal]):
    model = CalendarProposal

    async def next_confirmed(self, generation: str, now: datetime) -> CalendarProposal | None:
        table = self.model
        stmt = (
            select(table)
            .where(
                table.user_id == self.user_id,
                table.connection_generation == generation,
                table.synced_at.is_not(None),
                table.starts_at >= now,
            )
            .order_by(table.starts_at, table.id)
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def supersede(self, row: CalendarProposal) -> None:
        table = self.model
        await self.session.execute(
            update(table)
            .where(
                table.user_id == self.user_id,
                table.connection_generation == row.connection_generation,
                table.event_id == row.event_id,
                table.id != row.id,
                table.synced_at.is_not(None),
            )
            .values(starts_at=None)
        )
