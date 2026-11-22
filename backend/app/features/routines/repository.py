from datetime import date

from sqlalchemy import select, text

from app.db.models.routines import Routine, RoutineExecution
from app.db.repository import UserScopedRepository


class Routines(UserScopedRepository[Routine]):
    model = Routine

    async def begin_write(self) -> None:
        await self.session.execute(text("BEGIN IMMEDIATE"))

    async def rules(self) -> list[Routine]:
        stmt = select(Routine).where(Routine.user_id == self.user_id).order_by(Routine.created_at)
        return list((await self.session.scalars(stmt)).all())

    async def for_action(self, action: str) -> Routine | None:
        return await self.session.scalar(
            select(Routine).where(Routine.user_id == self.user_id, Routine.action == action)
        )

    async def due(self, day: date, hour: str) -> list[Routine]:
        stmt = select(Routine).where(
            Routine.user_id == self.user_id,
            Routine.enabled.is_(True),
            Routine.starts_on <= day,
            Routine.local_time <= hour,
        )
        return list((await self.session.scalars(stmt)).all())


class Executions(UserScopedRepository[RoutineExecution]):
    model = RoutineExecution

    async def occurrence(self, routine_id: str, occurrence: str) -> RoutineExecution | None:
        stmt = select(RoutineExecution).where(
            RoutineExecution.user_id == self.user_id,
            RoutineExecution.routine_id == routine_id,
            RoutineExecution.occurrence == occurrence,
        )
        return await self.session.scalar(stmt)

    async def recent(self, routine_id: str) -> list[RoutineExecution]:
        stmt = (
            select(RoutineExecution)
            .where(
                RoutineExecution.user_id == self.user_id,
                RoutineExecution.routine_id == routine_id,
            )
            .order_by(RoutineExecution.created_at.desc(), RoutineExecution.id)
            .limit(30)
        )
        return list((await self.session.scalars(stmt)).all())
