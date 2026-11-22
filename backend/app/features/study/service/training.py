from collections.abc import Awaitable, Callable
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.runner import SessionRunner
from app.core.errors import AppError
from app.db.models.study import StudySession
from app.features.conversations.service import (
    TRAINING_SCOPE,
    ConversationQuestionIn,
    ConversationStarted,
    ConversationThread,
    TurnOptions,
    ensure_conversation,
    read_conversation,
    submit_turn,
)
from app.features.study.repository import StudyRepository
from app.features.study.service.finish import finished_of, study_not_found
from app.features.study.service.runtime import StudyRuntime
from app.features.study.service.sessions import _live, _settle_kept, study_already_open
from app.features.study.training_schemas import TrainingSessionOut, TrainingStart
from app.mcp.recorder import ACTIVE

GREETING = "Qu’aimerais-tu travailler aujourd’hui ? Tu peux choisir un sujet ou une leçon."
TrainingLink = Callable[[AsyncSession, str], Awaitable[None]]


def thread_for(study_id: str) -> ConversationThread:
    return ConversationThread(study_id, TRAINING_SCOPE, study_id)


async def training_row(db: AsyncSession, user_id: str, study_id: str) -> StudySession:
    row = await StudyRepository(db, user_id).get_fresh(study_id)
    if row is None or row.kind != TRAINING_SCOPE:
        raise study_not_found()
    return row


async def training_out(db: AsyncSession, row: StudySession) -> TrainingSessionOut:
    conversation = await read_conversation(db, row.user_id, row.id)
    if conversation is None:
        raise study_not_found()
    done = finished_of(row)
    return TrainingSessionOut.model_validate(
        {
            "id": row.id,
            "mode": row.mode,
            "status": row.status,
            "started_at": row.created_at,
            "ended_at": row.ended_at,
            "minutes": row.minutes,
            "summary": row.summary,
            "flashcards_created": done.flashcards_created,
            "skills": [{"name": name, "level": level} for name, level in done.skills],
            "greeting": GREETING,
            "conversation": conversation,
        }
    )


async def open_training(db: AsyncSession, user_id: str) -> TrainingSessionOut | None:
    row = await StudyRepository(db, user_id).open_one()
    return await training_out(db, row) if row is not None and row.kind == TRAINING_SCOPE else None


async def _open_or_replace(repo: StudyRepository, now: datetime) -> StudySession | None:
    row = await repo.open_one()
    if row is not None and row.kind == TRAINING_SCOPE:
        return row
    live = await _live(repo.session, repo.user_id, now)
    if live is not None:
        raise study_already_open(live[0])
    return None


async def _commit_opening(db: AsyncSession, row: StudySession, link: TrainingLink | None) -> None:
    if link is not None:
        await link(db, row.id)
    if recorder := ACTIVE.get():
        await recorder.persist_in(db)
    await db.commit()


async def start_training(
    rt: StudyRuntime, user_id: str, body: TrainingStart, *, link: TrainingLink | None = None
) -> tuple[TrainingSessionOut, bool]:
    async with rt.study_lock(user_id):
        await _settle_kept(rt, user_id)
        async with rt.session_factory() as db:
            repo = StudyRepository(db, user_id)
            now = rt.now()
            existing = await _open_or_replace(repo, now)
            if existing is not None:
                if link is not None:
                    await _commit_opening(db, existing, link)
                return await training_out(db, existing), False
            try:
                row = await repo.add(
                    kind=TRAINING_SCOPE,
                    mode=body.mode,
                    created_at=now,
                    updated_at=now,
                )
                await ensure_conversation(db, user_id, thread_for(row.id))
                await _commit_opening(db, row, link)
            except IntegrityError:
                await db.rollback()
                existing = await _open_or_replace(repo, now)
                if existing is None:
                    raise
                if link is not None:
                    await _commit_opening(db, existing, link)
                return await training_out(db, existing), False
            return await training_out(db, row), True


async def start_direct_training(rt: StudyRuntime, user_id: str, link: TrainingLink) -> None:
    """Ouvre ou reprend un training et rattache son appelant dans la même transaction."""
    await start_training(rt, user_id, TrainingStart(mode="direct"), link=link)


async def talk_to_tutor(
    runner: SessionRunner,
    db: AsyncSession,
    user_id: str,
    study_id: str,
    body: ConversationQuestionIn,
) -> ConversationStarted:
    await training_row(db, user_id, study_id)

    async def authorize(tx: AsyncSession) -> TurnOptions:
        row = await training_row(tx, user_id, study_id)
        if row.status != "open":
            raise AppError("training_closed", "Cette session training est terminée.", 409)
        return TurnOptions(mode=row.mode)

    return await submit_turn(runner, db, user_id, thread_for(study_id), body, authorize)
