from collections.abc import Awaitable, Callable
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.runner import SessionRunner
from app.db.models.study import StudySession
from app.features.conversations.service import (
    TRAINING_SCOPE,
    ConversationQuestionIn,
    ConversationStarted,
    ConversationThread,
    TurnOptions,
    checked_lesson_ids,
    ensure_conversation,
    read_conversation,
    require_chat,
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
    thread = await require_chat(db, row.user_id, TRAINING_SCOPE, row.id)
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
            "lesson_ids": thread.lesson_ids,
        }
    )


async def open_training(db: AsyncSession, user_id: str) -> TrainingSessionOut | None:
    repo = StudyRepository(db, user_id)
    row = await repo.open_one()
    if row is None or row.kind != TRAINING_SCOPE:
        row = await repo.recent_independent_training()
    return await training_out(db, row) if row is not None else None


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


async def _insert_training(
    repo: StudyRepository, body: TrainingStart, now: datetime, link: TrainingLink | None
) -> StudySession:
    db, user_id = repo.session, repo.user_id
    lesson_ids = await checked_lesson_ids(db, user_id, body.lesson_ids)
    row = await repo.add(
        kind=TRAINING_SCOPE,
        independent=body.new_conversation,
        mode=body.mode,
        created_at=now,
        updated_at=now,
    )
    thread = await ensure_conversation(db, user_id, thread_for(row.id))
    thread.lesson_ids = lesson_ids
    await _commit_opening(db, row, link)
    return row


async def start_training(
    rt: StudyRuntime, user_id: str, body: TrainingStart, *, link: TrainingLink | None = None
) -> tuple[TrainingSessionOut, bool]:
    async with rt.study_lock(user_id):
        if not body.new_conversation:
            await _settle_kept(rt, user_id)
        async with rt.session_factory() as db:
            repo = StudyRepository(db, user_id)
            now = rt.now()
            if body.new_conversation:
                return await training_out(db, await _insert_training(repo, body, now, link)), True
            existing = await _open_or_replace(repo, now)
            if existing is not None:
                if link is not None:
                    await _commit_opening(db, existing, link)
                return await training_out(db, existing), False
            try:
                row = await _insert_training(repo, body, now, link)
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
    await require_chat(db, user_id, TRAINING_SCOPE, study_id)

    async def authorize(tx: AsyncSession) -> TurnOptions:
        row = await training_row(tx, user_id, study_id)
        thread = await require_chat(tx, user_id, TRAINING_SCOPE, study_id)
        return TurnOptions(mode=row.mode, lesson_ids=thread.lesson_ids)

    return await submit_turn(runner, db, user_id, thread_for(study_id), body, authorize)
