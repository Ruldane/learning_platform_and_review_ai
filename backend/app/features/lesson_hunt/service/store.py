"""Publier le brouillon ou le bilan seulement dans la session chargée de cette étape."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.lesson_hunt_port import ErrorPair, HuntAssessment, HuntContext
from app.core.errors import AppError
from app.db.models.lesson_hunt import LessonHunt
from app.features.lesson_hunt.repository import HuntRepository
from app.features.lesson_hunt.service.exercise import apply_edits


async def _assigned(repo: HuntRepository, hunt_id: str, session_id: str) -> LessonHunt:
    row = await repo.require(hunt_id)
    if row.session_id != session_id:
        raise AppError("lesson_hunt_changed", "L’exercice de lecture a changé. Relis-le.", 409)
    return row


class AgentLessonHuntStore:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def context(self, user_id: str, hunt_id: str, session_id: str) -> HuntContext:
        async with self._factory() as db:
            row = await _assigned(HuntRepository(db, user_id), hunt_id, session_id)
            return HuntContext(
                row.title,
                row.source,
                ErrorPair.model_validate(row.errors) if row.errors else None,
                row.responses,
                row.stage,
            )

    async def publish(
        self, user_id: str, hunt_id: str, session_id: str, changes: ErrorPair
    ) -> None:
        async with self._factory() as db:
            repo = HuntRepository(db, user_id)
            row = await _assigned(repo, hunt_id, session_id)
            if row.stage != "preparing":
                return
            try:
                exercise = apply_edits(row.source, changes)
            except ValueError:
                raise AppError(
                    "lesson_hunt_invalid",
                    "Les deux passages proposés ne correspondent pas au chapitre.",
                    422,
                ) from None
            await repo.replace(
                row, stage="ready", exercise=exercise, errors=changes.model_dump(mode="json")
            )
            await db.commit()

    async def assess(
        self, user_id: str, hunt_id: str, session_id: str, feedback: HuntAssessment
    ) -> None:
        async with self._factory() as db:
            repo = HuntRepository(db, user_id)
            row = await _assigned(repo, hunt_id, session_id)
            if row.stage != "reviewing":
                return
            await repo.replace(row, stage="complete", assessment=feedback.model_dump(mode="json"))
            await db.commit()
