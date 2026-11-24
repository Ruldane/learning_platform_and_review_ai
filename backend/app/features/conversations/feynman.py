"""Conversation routes and idempotent submission of the Feynman review."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.runner import SessionRunner
from app.agents.tools.feynman_port import FEYNMAN_IDE, FEYNMAN_LESSON, FEYNMAN_SCOPES
from app.core.caller import Caller
from app.core.clock import local_today, user_zone
from app.core.errors import AppError
from app.core.skills import evidence
from app.db.base import utcnow
from app.db.models.conversations import ConversationTurn
from app.features.conversations.feynman_schemas import (
    FeynmanData,
    FeynmanFileStart,
    FeynmanReport,
    FeynmanRunOut,
    FeynmanSaved,
    FeynmanStart,
)
from app.features.conversations.feynman_source import file_source, lesson_source
from app.features.conversations.lesson_context import lesson_version
from app.features.conversations.repository import ConversationRepository, TurnRepository
from app.features.conversations.schemas import ConversationQuestionIn, ConversationStarted
from app.features.conversations.service import ConversationThread, TurnOptions, submit_turn
from app.features.ide.service import IdeService
from app.features.lessons.service.lessons import get_lesson
from app.features.quiz.service.cards import NewCard, add_cards
from app.features.sessions.service import session_facts
from app.features.settings.service import SettingsService
from app.features.skills.service import SkillsService


def _missing() -> AppError:
    return AppError("feynman_not_found", "Explication introuvable.", 404)


async def _check_source(db: AsyncSession, user: str, subject_id: str, scope: str) -> None:
    if scope == FEYNMAN_LESSON:
        lesson = await get_lesson(db, user, subject_id)
        if lesson.status != "ready":
            raise AppError("lesson_not_ready", "This lesson is not ready yet.", 409)
    else:
        await IdeService(db, user, None, Caller("app", "feynman")).get_session(subject_id)


def _view(turn: ConversationTurn, status: str) -> FeynmanRunOut:
    data = FeynmanData.model_validate(turn.feynman)
    return FeynmanRunOut.model_validate(
        {
            "id": turn.id,
            "session_id": turn.session_id,
            "status": status,
            "source": data.source,
            "report": data.report if status == "completed" else None,
        }
    )


async def latest(db: AsyncSession, user: str, subject_id: str, scope: str) -> FeynmanRunOut | None:
    await _check_source(db, user, subject_id, scope)
    thread = ConversationThread.for_subject(user, scope, subject_id)
    found = await TurnRepository(db, user).latest(thread.id)
    return _view(*found) if found is not None else None


async def start(
    runner: SessionRunner, db: AsyncSession, user: str, subject_id: str, body: FeynmanStart
) -> ConversationStarted:
    file = body.path if isinstance(body, FeynmanFileStart) else None
    scope = FEYNMAN_IDE if file is not None else FEYNMAN_LESSON
    await _check_source(db, user, subject_id, scope)
    thread = ConversationThread.for_subject(user, scope, subject_id)
    question = "Explain the lesson." if file is None else f"Explain '{file}'."
    message = ConversationQuestionIn(
        request_id=body.request_id, question=question, strong=body.strong
    )

    async def authorize(tx: AsyncSession) -> TurnOptions:
        if file is None:
            data, raw = await lesson_source(tx, user, subject_id)
        else:
            data, raw = await file_source(tx, user, subject_id, file)
        if not raw.strip():
            raise AppError("feynman_empty_source", "The saved source is empty.", 422)
        return TurnOptions(lesson_version=lesson_version(raw), feynman=data)

    return await submit_turn(runner, db, user, thread, message, authorize)


async def _owned(
    db: AsyncSession, user: str, turn_id: str, *, lock: bool = False
) -> ConversationTurn:
    repo = TurnRepository(db, user)
    turn = await (repo.lock_completed(turn_id) if lock else repo.get(turn_id))
    if turn is None or turn.feynman is None:
        raise _missing()
    thread = await ConversationRepository(db, user).get(turn.thread_id)
    if thread is None or thread.scope not in FEYNMAN_SCOPES:
        raise _missing()
    await _check_source(db, user, thread.subject_id, thread.scope)
    return turn


async def read(db: AsyncSession, user: str, turn_id: str) -> FeynmanRunOut:
    turn = await _owned(db, user, turn_id)
    facts = await session_facts(db, user, turn.session_id)
    if facts is None:
        raise _missing()
    return _view(turn, facts.status)


async def _save_cards(
    db: AsyncSession, user: str, turn_id: str, data: FeynmanData, report: FeynmanReport
) -> int:
    settings = await SettingsService(db, user).get()
    return await add_cards(
        db,
        user,
        [
            NewCard(item.front, item.back, data.skill, data.module_id, "feynman", turn_id)
            for item in report.cards
        ],
        local_today(user_zone(settings.timezone)),
    )


async def accept(db: AsyncSession, user: str, turn_id: str) -> FeynmanSaved:
    turn = await _owned(db, user, turn_id, lock=True)
    data = FeynmanData.model_validate(turn.feynman)
    report = data.report
    if report is None:
        raise _missing()
    if report.saved is not None:
        return report.saved
    cards = await _save_cards(db, user, turn_id, data, report)
    if report.proof_skill:
        proof = evidence("feynman", turn.id, "Successful Feynman explanation", utcnow())
        await SkillsService(db, user).raise_levels([report.proof_skill], "en_cours", proof)
    report.saved = FeynmanSaved(cards_added=cards, proof_saved=report.proof_skill is not None)
    turn.feynman = data.model_dump(mode="json")
    await db.commit()
    return report.saved
