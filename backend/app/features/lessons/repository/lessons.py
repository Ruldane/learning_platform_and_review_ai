import builtins

from sqlalchemy import select

from app.db.models.lessons import Lesson
from app.db.repository import UserScopedRepository


class LessonRepository(UserScopedRepository[Lesson]):
    """Leçons d'un utilisateur, une par module. Lectures fraîches (`populate_existing`) : sous le
    verrou des leçons d'un programme, une requête voit ce que la précédente a commité."""

    model = Lesson

    async def get_fresh(self, lesson_id: str) -> Lesson | None:
        stmt = (
            select(Lesson)
            .where(Lesson.id == lesson_id, Lesson.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def by_module(self, module_id: str) -> Lesson | None:
        stmt = (
            select(Lesson)
            .where(Lesson.user_id == self.user_id, Lesson.module_id == module_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def for_program(self, program_id: str) -> builtins.list[Lesson]:
        stmt = (
            select(Lesson)
            .where(Lesson.user_id == self.user_id, Lesson.program_id == program_id)
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())
