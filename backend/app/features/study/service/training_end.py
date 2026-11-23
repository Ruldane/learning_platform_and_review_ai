import logging
from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.runner import SessionRunner
from app.agents.tools.conversation_port import TRAINING_TUTOR
from app.agents.tools.study_port import StudyFinished
from app.core.errors import AppError
from app.core.skills import evidence
from app.db.base import utcnow
from app.db.models.study import StudySession
from app.features.capture.service.journal import JournalLinks, add_entry
from app.features.conversations.service import (
    TRAINING_SCOPE,
    cancel_conversation_turn,
    checked_lesson_ids,
    cited_study_material,
    require_chat,
    require_idle_conversation,
)
from app.features.memory.service.skill_levels import reflect_skill_levels
from app.features.quiz.service.cards import NewCard, add_cards
from app.features.skills.service import SkillsService
from app.features.study.repository import StudyReadRepository, StudyRepository
from app.features.study.service.control import clamped_minutes
from app.features.study.service.finish import CEILING, finished_of
from app.features.study.service.runtime import StudyRuntime
from app.features.study.service.training import training_out, training_row
from app.features.study.training_schemas import (
    TrainingCancel,
    TrainingFinish,
    TrainingLessonsUpdate,
    TrainingModeUpdate,
    TrainingSessionOut,
    TrainingUpdate,
)
from app.mcp.recorder import ACTIVE

logger = logging.getLogger(__name__)


async def _followup(
    rt: StudyRuntime, db: AsyncSession, row: StudySession, body: TrainingFinish
) -> StudyFinished:
    now, user_id = rt.now(), row.user_id
    minutes = clamped_minutes(body.worked_minutes, row.created_at, now)
    today = await rt.today(db, user_id)
    cited, missed = await cited_study_material(db, user_id, row.id)
    reads = StudyReadRepository(db, user_id)
    modules = {}
    for lesson_id in sorted(cited):
        lesson = await reads.lesson(lesson_id)
        if lesson is None or lesson.status != "ready":
            continue
        module = await reads.module(lesson.module_id)
        if module is not None and not module.skipped and module.program_id == lesson.program_id:
            modules[lesson_id] = module
    cards = [
        NewCard(card.front, card.back, None, modules[str(card.lesson_id)].id, "study", row.id)
        for card in missed
        if str(card.lesson_id) in modules
    ]
    skills = [str(skill) for module in modules.values() for skill in module.skills]
    label = f"Session training ({today:%d/%m})"
    changed = await SkillsService(db, user_id).raise_levels(
        skills, CEILING, evidence("study", row.id, label, now)
    )
    count = await add_cards(db, user_id, cards, today)
    result = StudyFinished(minutes, [], count, changed)
    row.minutes, row.worked_minutes = minutes, minutes
    row.status, row.ended_at = "finished", now
    row.summary = f"Session training terminée. {minutes} min et {count} fiche(s) de révision."
    row.outcome = {"result": asdict(result)}
    await add_entry(
        db,
        user_id,
        kind="study_session",
        text=row.summary,
        occurred_on=today,
        ref_key=f"study:{row.id}",
        links=JournalLinks(study_session_id=row.id),
        data={"kind": "training", "minutes": minutes, "summary": row.summary},
    )
    return result


async def _apply(
    rt: StudyRuntime, user_id: str, study_id: str, body: TrainingUpdate
) -> tuple[StudyFinished | None, str | None]:
    async with rt.session_factory() as db:
        repo = StudyRepository(db, user_id)
        row = await repo.claim_training(
            study_id, include_closed=isinstance(body, (TrainingModeUpdate, TrainingLessonsUpdate))
        )
        if row is None:
            closed = await training_row(db, user_id, study_id)
            if isinstance(body, (TrainingModeUpdate, TrainingLessonsUpdate)):
                raise AppError("training_closed", "Cette session training est terminée.", 409)
            return finished_of(closed) if isinstance(body, TrainingFinish) else None, None
        result, cancelled = None, None
        if isinstance(body, (TrainingModeUpdate, TrainingLessonsUpdate)):
            thread = await require_chat(db, user_id, TRAINING_SCOPE, study_id)
            if isinstance(body, TrainingModeUpdate):
                row.mode = body.mode
            else:
                thread.lesson_ids = await checked_lesson_ids(db, user_id, body.lesson_ids)
            thread.updated_at = utcnow()
        elif isinstance(body, TrainingCancel):
            cancelled = await cancel_conversation_turn(db, user_id, row.id)
            row.status, row.ended_at = "cancelled", rt.now()
        else:
            await require_idle_conversation(db, user_id, row.id)
            result = await _followup(rt, db, row, body)
        if recorder := ACTIVE.get():
            await recorder.persist_in(db)
        await db.commit()
        return result, cancelled


async def update_training(
    runner: SessionRunner, rt: StudyRuntime, user_id: str, study_id: str, body: TrainingUpdate
) -> TrainingSessionOut:
    async with rt.study_lock(user_id):
        done, cancelled = await _apply(rt, user_id, study_id, body)
        if cancelled is not None:
            await runner.settle_cancelled(user_id, cancelled)
    if done is not None and done.skills:
        try:
            await reflect_skill_levels(
                rt.memory,
                user_id,
                done.skills,
                author=TRAINING_TUTOR,
                session_id=None,
                reason="Session training.",
            )
        except Exception:
            logger.warning("Acquis non reflétés après le training : étude %s", study_id)
    async with rt.session_factory() as db:
        return await training_out(db, await training_row(db, user_id, study_id))
