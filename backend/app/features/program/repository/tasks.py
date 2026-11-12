import builtins
from collections.abc import Collection

from sqlalchemy import delete, func, select

from app.db.models.program import Task
from app.db.repository import UserScopedRepository


class TaskRepository(UserScopedRepository[Task]):
    """Tâches d'un utilisateur ; lectures fraîches, comme `ProgramRepository`."""

    model = Task

    async def get_fresh(self, task_id: str) -> Task | None:
        stmt = (
            select(Task)
            .where(Task.id == task_id, Task.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def program_of(self, task_id: str) -> str | None:
        stmt = select(Task.program_id).where(Task.id == task_id, Task.user_id == self.user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def for_program(self, program_id: str) -> builtins.list[Task]:
        stmt = (
            select(Task)
            .where(Task.user_id == self.user_id, Task.program_id == program_id)
            .order_by(Task.rank)
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def next_rank(self, module_id: str) -> int:
        stmt = select(func.max(Task.rank)).where(
            Task.user_id == self.user_id, Task.module_id == module_id
        )
        current = (await self.session.execute(stmt)).scalar_one_or_none()
        return 0 if current is None else int(current) + 1

    async def delete_many(self, task_ids: Collection[str]) -> None:
        if not task_ids:
            return
        stmt = delete(Task).where(
            Task.user_id == self.user_id, Task.id.in_(builtins.list(task_ids))
        )
        await self.session.execute(stmt)
