import builtins
from datetime import datetime

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

    async def recent_settled(
        self, after: datetime | None, before: datetime | None, limit: int
    ) -> builtins.list[Lesson]:
        """Les leçons prêtes ou en échec dont le dernier changement est dans `[after, before]`
        (bornes incluses), plus récentes d'abord (fil d'activité)."""
        stmt = select(Lesson).where(
            Lesson.user_id == self.user_id, Lesson.status.in_(("ready", "failed"))
        )
        if after is not None:
            stmt = stmt.where(Lesson.updated_at >= after)
        if before is not None:
            stmt = stmt.where(Lesson.updated_at <= before)
        stmt = stmt.order_by(Lesson.updated_at.desc(), Lesson.id.desc()).limit(limit)
        return builtins.list((await self.session.execute(stmt)).scalars())
