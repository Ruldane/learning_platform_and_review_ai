"""Start the critical reading from a published version and receive the answers."""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.launcher import SessionLauncher
from app.agents.tools.lesson_hunt_port import HUNT_GRAPH, ErrorPair, HuntAssessment
from app.core.errors import AppError
from app.db.models.lesson_hunt import LessonHunt
from app.features.lesson_hunt.repository import HuntRepository
from app.features.lesson_hunt.schemas import HuntAnswers, HuntOut, HuntStarted
from app.features.lessons.service.lessons import get_lesson
from app.features.sessions.service import session_facts

_FAILED = frozenset({"failed", "cancelled", "expired"})


async def _failed(db: AsyncSession, user_id: str, row: LessonHunt) -> bool:
    facts = await session_facts(db, user_id, row.session_id)
    return facts is not None and facts.status in _FAILED


async def start_hunt(launcher: SessionLauncher, user_id: str, lesson_id: str) -> HuntStarted:
    hunt_id = str(uuid4())

    async def prepare(db: AsyncSession, session_id: str) -> None:
        lesson = await get_lesson(db, user_id, lesson_id)
        if lesson.status != "ready" or not lesson.markdown.strip():
            raise AppError("lesson_unpublished", "Publish this lesson first.", 409)
        db.add(
            LessonHunt(
                id=hunt_id,
                user_id=user_id,
                lesson_id=lesson_id,
                title=lesson.title,
                source=lesson.markdown,
                session_id=session_id,
                stage="preparing",
            )
        )

    session_id = await launcher.start(
        user_id,
        HUNT_GRAPH,
        {"hunt_id": hunt_id},
        subject_type=HUNT_GRAPH,
        subject_id=hunt_id,
        prepare=prepare,
    )
    return HuntStarted(hunt_id=hunt_id, session_id=session_id)


async def submit_answers(
    launcher: SessionLauncher, user_id: str, hunt_id: str, answers: HuntAnswers
) -> HuntStarted:
    async def prepare(db: AsyncSession, session_id: str) -> None:
        repo = HuntRepository(db, user_id)
        row = await repo.require(hunt_id)
        retry = row.stage == "reviewing" and await _failed(db, user_id, row)
        if row.stage != "ready" and not retry:
            raise AppError("lesson_hunt_not_ready", "The exercise cannot receive answers.", 409)
        await repo.replace(
            row, stage="reviewing", session_id=session_id, responses=answers.responses
        )

    session_id = await launcher.start(
        user_id,
        HUNT_GRAPH,
        {"hunt_id": hunt_id},
        subject_type=HUNT_GRAPH,
        subject_id=hunt_id,
        prepare=prepare,
    )
    return HuntStarted(hunt_id=hunt_id, session_id=session_id)


async def get_hunt(db: AsyncSession, user_id: str, hunt_id: str) -> HuntOut:
    row = await HuntRepository(db, user_id).require(hunt_id)
    pending = row.stage in {"preparing", "reviewing"}
    finished = row.stage == "complete"
    result = HuntOut(
        id=row.id,
        lesson_id=row.lesson_id,
        title=row.title,
        stage="failed" if pending and await _failed(db, user_id, row) else row.stage,
        session_id=row.session_id,
        exercise=row.exercise,
        responses=row.responses,
        corrections=None,
        assessment=None,
    )
    if finished and row.errors is not None and row.assessment is not None:
        result.corrections = ErrorPair.model_validate(row.errors).edits
        result.assessment = HuntAssessment.model_validate(row.assessment)
    return result
