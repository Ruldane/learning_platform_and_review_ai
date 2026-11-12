import builtins

from sqlalchemy import delete, func, literal_column, select

from app.db.models.lessons import Lesson, Resource
from app.db.models.program import Module, Program, Week
from app.db.repository import UserScopedRepository


class ProgramRepository(UserScopedRepository[Program]):
    """Programmes d'un utilisateur. Lectures fraîches (`populate_existing`) : sous le verrou d'un
    programme, une requête voit ce que la précédente a commité."""

    model = Program

    async def get_fresh(self, program_id: str) -> Program | None:
        stmt = (
            select(Program)
            .where(Program.id == program_id, Program.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def by_session(self, session_id: str) -> Program | None:
        """Le programme écrit par cette session du Stratège (le plus ancien s'il y en avait)."""
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
        """Semaines du programme, et en cascade leurs modules et tâches (clés étrangères)."""
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
    """Leçon et nombre de ressources de chaque module d'un programme (lecture seule)."""

    model = Lesson

    async def lessons(self, program_id: str) -> dict[str, tuple[str, str]]:
        """`module → (leçon, statut)`."""
        stmt = select(Lesson.module_id, Lesson.id, Lesson.status).where(
            Lesson.user_id == self.user_id, Lesson.program_id == program_id
        )
        return {row[0]: (row[1], row[2]) for row in (await self.session.execute(stmt)).all()}

    async def resource_counts(self, program_id: str) -> dict[str, int]:
        stmt = (
            select(Resource.module_id, func.count())
            .where(Resource.user_id == self.user_id, Resource.program_id == program_id)
            .group_by(Resource.module_id)
        )
        return {row[0]: int(row[1]) for row in (await self.session.execute(stmt)).all()}
