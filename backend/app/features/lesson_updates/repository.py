from sqlalchemy import select, update

from app.db.models.lesson_updates import LessonUpdate
from app.db.repository import UserScopedRepository


class UpdatesRepository(UserScopedRepository[LessonUpdate]):
    model = LessonUpdate

    async def known_versions(self) -> dict[tuple[str, str, str], str | None]:
        stmt = select(
            LessonUpdate.lesson_id,
            LessonUpdate.library,
            LessonUpdate.version,
            LessonUpdate.base_hash,
            LessonUpdate.publication_session_id,
        ).where(LessonUpdate.user_id == self.user_id)
        return {
            (lesson, library, version): None if approved else digest
            for lesson, library, version, digest, approved in await self.session.execute(stmt)
        }

    async def save_draft(self, proposal_id: str, session_id: str, draft: dict[str, object]) -> bool:
        stmt = (
            update(LessonUpdate)
            .where(
                LessonUpdate.id == proposal_id,
                LessonUpdate.user_id == self.user_id,
                LessonUpdate.preparation_session_id == session_id,
            )
            .values(draft=draft)
            .returning(LessonUpdate.id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    async def listed(self, lesson_id: str) -> list[LessonUpdate]:
        stmt = (
            select(LessonUpdate)
            .where(LessonUpdate.user_id == self.user_id, LessonUpdate.lesson_id == lesson_id)
            .order_by(LessonUpdate.created_at.desc(), LessonUpdate.id.desc())
            .limit(30)
        )
        return list(await self.session.scalars(stmt))
