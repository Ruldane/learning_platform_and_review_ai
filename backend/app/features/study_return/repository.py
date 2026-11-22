from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.lessons import Lesson
from app.db.models.study import StudySession
from app.db.models.study_return import StudyReturn


async def current(db: AsyncSession, user_id: str) -> StudyReturn | None:
    return await db.scalar(select(StudyReturn).where(StudyReturn.user_id == user_id))


async def last_finished(db: AsyncSession, user_id: str) -> tuple[StudySession, str | None] | None:
    stmt = (
        select(StudySession, Lesson.title)
        .outerjoin(Lesson, (Lesson.id == StudySession.lesson_id) & (Lesson.user_id == user_id))
        .where(
            StudySession.user_id == user_id,
            StudySession.status == "finished",
            StudySession.ended_at.is_not(None),
            StudySession.kind.in_(("guided", "training")),
        )
        .order_by(StudySession.ended_at.desc(), StudySession.id)
        .limit(1)
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        return None
    return row[0], row[1]


async def training_open(db: AsyncSession, user_id: str, training_id: str) -> bool:
    active = await db.scalar(
        select(StudySession.id).where(
            StudySession.user_id == user_id,
            StudySession.id == training_id,
            StudySession.kind == "training",
            StudySession.status == "open",
        )
    )
    return active is not None
