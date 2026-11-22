from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.grade_appeals_port import AppealContext, AppealReading
from app.core.errors import AppError
from app.db.base import utcnow
from app.db.models.grade_appeals import GradeAppeal
from app.features.grade_appeals.repository import GradeAppeals
from app.features.grade_appeals.schemas import GradeAppealSource


async def _bound(db: AsyncSession, user_id: str, appeal_id: str, session_id: str) -> GradeAppeal:
    row = await GradeAppeals(db, user_id).require(appeal_id)
    if row.session_id != session_id:
        raise AppError("grade_appeal_changed", "Cette relecture n’est plus active.", 409)
    return row


class AgentGradeAppealsStore:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def context(self, user_id: str, appeal_id: str, session_id: str) -> AppealContext:
        async with self._factory() as db:
            row = await _bound(db, user_id, appeal_id, session_id)
            source = GradeAppealSource.model_validate(row.source)
            return AppealContext(
                criterion=source.criterion.criterion,
                submission=source.submission,
                reason=row.reason,
                complete=row.second is not None,
            )

    async def save(
        self, user_id: str, appeal_id: str, session_id: str, reading: AppealReading
    ) -> None:
        async with self._factory.begin() as db:
            await db.execute(text("BEGIN IMMEDIATE"))
            row = await _bound(db, user_id, appeal_id, session_id)
            if row.second is None:
                row.second = reading.model_dump()
                row.reviewed_at = utcnow()
