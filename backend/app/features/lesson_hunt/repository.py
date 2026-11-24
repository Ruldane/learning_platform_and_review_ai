"""Critical reading exercises per account and per session."""

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.lesson_hunt import LessonHunt


class HuntRepository:
    def __init__(self, db: AsyncSession, user_id: str) -> None:
        self._db = db
        self._user_id = user_id

    async def require(self, hunt_id: str) -> LessonHunt:
        query = select(LessonHunt).where(
            LessonHunt.id == hunt_id, LessonHunt.user_id == self._user_id
        )
        row = await self._db.scalar(query)
        if row is None:
            raise AppError("lesson_hunt_not_found", "Reading exercise not found.", 404)
        return row

    async def replace(self, row: LessonHunt, **changes: Any) -> None:
        result = await self._db.execute(
            update(LessonHunt)
            .where(
                LessonHunt.id == row.id,
                LessonHunt.user_id == self._user_id,
                LessonHunt.stage == row.stage,
                LessonHunt.session_id == row.session_id,
            )
            .values(**changes)
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise AppError(
                "lesson_hunt_changed", "The reading exercise has changed. Read it again.", 409
            )
