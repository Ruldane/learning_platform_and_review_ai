"""Read for the program (`followup.tick_week_quiz`): the modules whose quiz has a graded
attempt. The other features go through the service (contract 2)."""

from collections.abc import Collection

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.quiz.repository import AttemptRepository


async def graded_modules(db: AsyncSession, user_id: str, module_ids: Collection[str]) -> set[str]:
    return await AttemptRepository(db, user_id).graded_modules(module_ids)
