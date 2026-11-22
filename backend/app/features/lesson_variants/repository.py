from sqlalchemy import select

from app.db.models.lesson_variants import LessonVariantSet
from app.db.repository import UserScopedRepository


class LessonVariants(UserScopedRepository[LessonVariantSet]):
    model = LessonVariantSet

    async def for_revision(self, lesson_id: str, revision: str) -> LessonVariantSet | None:
        stmt = select(self.model).where(
            self.model.user_id == self.user_id,
            self.model.lesson_id == lesson_id,
            self.model.revision == revision,
        )
        return await self.session.scalar(stmt)

    async def history(self) -> list[LessonVariantSet]:
        stmt = (
            select(self.model)
            .where(self.model.user_id == self.user_id)
            .order_by(self.model.created_at.desc(), self.model.id.desc())
        )
        return list(await self.session.scalars(stmt))
