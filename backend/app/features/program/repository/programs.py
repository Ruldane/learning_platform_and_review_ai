import builtins

from sqlalchemy import delete, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.lessons import Lesson, Resource
from app.db.models.program import Module, Program, Week
from app.db.repository import UserScopedRepository


class ProgramRepository(UserScopedRepository[Program]):
    """A user's programs. Fresh reads (`populate_existing`): under a program's lock, a query sees
    what the previous one committed."""

    model = Program

    async def get_fresh(self, program_id: str) -> Program | None:
        stmt = (
            select(Program)
            .where(Program.id == program_id, Program.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def by_session(self, session_id: str) -> Program | None:
        """The program written by this Strategist session (the oldest if there were several)."""
        stmt = (
            select(Program)
            .where(Program.user_id == self.user_id, Program.session_id == session_id)
            .order_by(Program.created_at, literal_column("rowid"))
            .limit(1)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_recent(self) -> builtins.list[Program]:
        stmt = (
            select(Program)
            .where(Program.user_id == self.user_id)
            .order_by(Program.created_at.desc(), literal_column("rowid").desc())
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())


class WeekRepository(UserScopedRepository[Week]):
    model = Week

    async def for_program(self, program_id: str) -> builtins.list[Week]:
        stmt = (
            select(Week)
            .where(Week.user_id == self.user_id, Week.program_id == program_id)
            .order_by(Week.rank)
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def count_by_program(self) -> dict[str, int]:
        stmt = (
            select(Week.program_id, func.count())
            .where(Week.user_id == self.user_id)
            .group_by(Week.program_id)
        )
        return {row[0]: int(row[1]) for row in (await self.session.execute(stmt)).all()}

    async def delete_for_program(self, program_id: str) -> None:
        """Weeks of the program, and in cascade their modules and tasks (foreign keys)."""
        stmt = delete(Week).where(Week.user_id == self.user_id, Week.program_id == program_id)
        await self.session.execute(stmt)


class ModuleRepository(UserScopedRepository[Module]):
    model = Module

    async def for_program(self, program_id: str) -> builtins.list[Module]:
        stmt = (
            select(Module)
            .where(Module.user_id == self.user_id, Module.program_id == program_id)
            .order_by(Module.rank)
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())


class ModuleExtrasRepository(UserScopedRepository[Lesson]):
    """Lesson and number of resources of each module of a program (read-only)."""

    model = Lesson

    async def lessons(self, program_id: str) -> dict[str, tuple[str, str, str | None]]:
        """`module → (lesson, status, session)`."""
        stmt = select(Lesson.module_id, Lesson.id, Lesson.status, Lesson.session_id).where(
            Lesson.user_id == self.user_id, Lesson.program_id == program_id
        )
        rows = (await self.session.execute(stmt)).all()
        return {row[0]: (row[1], row[2], row[3]) for row in rows}

    async def resource_counts(self, program_id: str) -> dict[str, int]:
        stmt = (
            select(Resource.module_id, func.count())
            .where(Resource.user_id == self.user_id, Resource.program_id == program_id)
            .group_by(Resource.module_id)
        )
        return {row[0]: int(row[1]) for row in (await self.session.execute(stmt)).all()}


async def validated_programs(session: AsyncSession) -> builtins.list[tuple[str, str]]:
    """`(user, program)` of ALL validated programs, identifiers only.

    The ONLY read without `user_id` in phase 4 (D91, like D18 and D75): reserved for the scheduled
    lessons task (`app.scheduler`), which then re-runs each program under its user (all following
    reads filter by `user_id`)."""
    stmt = (
        select(Program.user_id, Program.id)
        .where(Program.status == "validated")
        .order_by(Program.created_at, literal_column("rowid"))
    )
    return [(row[0], row[1]) for row in (await session.execute(stmt)).all()]
