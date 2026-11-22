from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.daily import Project
from app.db.models.error_atlas import AtlasHypothesis, AtlasObservation
from app.db.models.study import Quiz, QuizAttempt

SOURCE_LIMIT = 30


def _hypotheses(user_id: str) -> Select[AtlasHypothesis]:
    return select(AtlasHypothesis).where(AtlasHypothesis.user_id == user_id)


async def list_hypotheses(db: AsyncSession, user_id: str) -> list[AtlasHypothesis]:
    return list(
        await db.scalars(
            _hypotheses(user_id).order_by(AtlasHypothesis.created_at, AtlasHypothesis.id)
        )
    )


async def hypothesis(db: AsyncSession, user_id: str, hypothesis_id: str) -> AtlasHypothesis | None:
    return await db.scalar(_hypotheses(user_id).where(AtlasHypothesis.id == hypothesis_id))


async def matching_label(db: AsyncSession, user_id: str, key: str) -> AtlasHypothesis | None:
    return await db.scalar(_hypotheses(user_id).where(AtlasHypothesis.label_key == key))


async def observations(
    db: AsyncSession, user_id: str, hypothesis_id: str | None = None
) -> list[AtlasObservation]:
    stmt = select(AtlasObservation).where(AtlasObservation.user_id == user_id)
    if hypothesis_id is not None:
        stmt = stmt.where(AtlasObservation.hypothesis_id == hypothesis_id)
    return list(await db.scalars(stmt.order_by(AtlasObservation.created_at, AtlasObservation.id)))


async def quiz_attempts(
    db: AsyncSession, user_id: str, quiz_id: str | None = None, attempt_id: str | None = None
) -> list[tuple[QuizAttempt, str]]:
    stmt = (
        select(QuizAttempt, Quiz.title)
        .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
        .where(
            QuizAttempt.user_id == user_id, Quiz.user_id == user_id, QuizAttempt.status == "graded"
        )
    )
    if quiz_id is not None and attempt_id is not None:
        stmt = stmt.where(Quiz.id == quiz_id, QuizAttempt.id == attempt_id)
    rows = await db.execute(
        stmt.order_by(QuizAttempt.created_at.desc(), QuizAttempt.id).limit(SOURCE_LIMIT)
    )
    return [(attempt, title) for attempt, title in rows]


async def project_evaluations(
    db: AsyncSession, user_id: str, project_id: str | None = None
) -> list[Project]:
    stmt = select(Project).where(
        Project.user_id == user_id, Project.status.in_(("validated", "to_redo"))
    )
    if project_id is not None:
        stmt = stmt.where(Project.id == project_id)
    return list(
        await db.scalars(stmt.order_by(Project.updated_at.desc(), Project.id).limit(SOURCE_LIMIT))
    )
