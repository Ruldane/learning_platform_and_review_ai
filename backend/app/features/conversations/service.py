from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.creation import PrepareSession
from app.agents.runtime.runner import SessionRunner
from app.agents.tools.conversation_port import CONVERSATION_GRAPH, TURN_TOKEN_LIMIT
from app.core.clock import local_moment, local_today, user_zone
from app.core.errors import AppError
from app.core.played import PLAY_CONTEXT
from app.db.base import new_id
from app.db.models.agents import OPEN_SESSION_STATES
from app.db.models.conversations import ConversationTurn
from app.features.conversations.lesson_context import lesson_material, lesson_version, ready_lesson
from app.features.conversations.repository import ConversationRepository, TurnRepository
from app.features.conversations.schemas import (
    ConversationMessageIn,
    ConversationStarted,
    ConversationTurnOut,
    ConversationUsage,
    LessonConversationOut,
)
from app.features.sessions.service import session_facts
from app.features.settings.service import SettingsService
from app.mcp.recorder import ACTIVE

LESSON_SCOPE = "lesson"
THREAD_TOKEN_LIMIT = 100_000
DAY_TOKEN_LIMIT = 300_000
TURN_LIMIT = 100


def _thread_id(user_id: str, scope: str, subject_id: str) -> str:
    # Permet à deux premières soumissions concurrentes de réserver le même fil dans prepare.
    return str(uuid5(NAMESPACE_URL, f"tremplin/conversations/{user_id}/{scope}/{subject_id}"))


async def _usage(repo: TurnRepository, thread_id: str) -> tuple[ConversationUsage, int]:
    zone = user_zone((await SettingsService(repo.session, repo.user_id).get()).timezone)
    day_start = local_moment(local_today(zone), "00:00", zone)
    thread, day, turns, reserved = await repo.usage(thread_id, day_start, TURN_TOKEN_LIMIT)
    return ConversationUsage(
        thread_tokens=thread,
        thread_token_limit=THREAD_TOKEN_LIMIT,
        day_tokens=day,
        day_token_limit=DAY_TOKEN_LIMIT,
        turns=turns,
        turn_limit=TURN_LIMIT,
    ), reserved


class _RepeatedRequest(Exception):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id


def _same_request(previous: ConversationTurn, message: ConversationMessageIn) -> str:
    if (previous.question, previous.passage, previous.passage_occurrence, previous.strong) != (
        message.question,
        message.passage,
        message.passage_occurrence,
        message.strong,
    ):
        raise AppError(
            "conversation_request_conflict",
            "L'identifiant de cette demande a déjà servi pour un autre message.",
            409,
        )
    return previous.session_id


async def _check_limits(repo: TurnRepository, thread_id: str) -> None:
    if any(status in OPEN_SESSION_STATES for _, status in await repo.turns(thread_id)):
        raise AppError(
            "conversation_busy", "Une réponse est déjà en cours dans cette conversation.", 409
        )
    usage, reserved = await _usage(repo, thread_id)
    if usage.turns >= usage.turn_limit:
        scope = "turns"
    elif usage.thread_tokens + TURN_TOKEN_LIMIT > usage.thread_token_limit:
        scope = "thread"
    elif usage.day_tokens + reserved + TURN_TOKEN_LIMIT > usage.day_token_limit:
        scope = "day"
    else:
        return
    raise AppError(
        "conversation_budget_reached",
        "Le budget de conversation est atteint.",
        429,
        {"scope": scope},
    )


async def read_lesson_conversation(
    db: AsyncSession, user_id: str, lesson_id: str
) -> LessonConversationOut | None:
    await ready_lesson(db, user_id, lesson_id)
    thread_id = _thread_id(user_id, LESSON_SCOPE, lesson_id)
    thread = await ConversationRepository(db, user_id).get(thread_id)
    if thread is None:
        return None
    repo = TurnRepository(db, user_id)
    turns = [
        ConversationTurnOut.model_validate(
            {
                name: status if name == "status" else getattr(row, name)
                for name in ConversationTurnOut.model_fields
            }
        )
        for row, status in await repo.turns(thread_id)
    ]
    usage, _ = await _usage(repo, thread_id)
    return LessonConversationOut.model_validate(
        {"id": thread.id, "lesson_id": lesson_id, "turns": turns, "usage": usage}
    )


def _reserve(
    user_id: str, lesson_id: str, thread_id: str, turn_id: str, message: ConversationMessageIn
) -> PrepareSession:
    async def prepare(db: AsyncSession, session_id: str) -> None:
        threads = ConversationRepository(db, user_id)
        turns = TurnRepository(db, user_id)
        _, markdown = await ready_lesson(db, user_id, lesson_id)
        request_id = str(message.request_id)
        if previous := await turns.by_request(thread_id, request_id):
            raise _RepeatedRequest(_same_request(previous, message))
        version = None
        if message.passage is not None:
            lesson_material(markdown, message.passage, message.passage_occurrence)
            version = lesson_version(markdown)
        await _check_limits(turns, thread_id)
        if await threads.get(thread_id) is None:
            await threads.add(id=thread_id, scope=LESSON_SCOPE, subject_id=lesson_id)
        recorder = ACTIVE.get()
        await turns.add(
            id=turn_id,
            thread_id=thread_id,
            request_id=request_id,
            session_id=session_id,
            question=message.question,
            passage=message.passage,
            passage_occurrence=message.passage_occurrence,
            lesson_version=version,
            strong=message.strong,
            mcp_call_id=recorder.call_id if recorder is not None else None,
        )
        if recorder is not None:
            await recorder.persist_in(db)

    return prepare


async def ask_lesson_professor(
    runner: SessionRunner,
    db: AsyncSession,
    user_id: str,
    lesson_id: str,
    message: ConversationMessageIn,
) -> ConversationStarted:
    thread_id = _thread_id(user_id, LESSON_SCOPE, lesson_id)
    if previous := await TurnRepository(db, user_id).by_request(thread_id, str(message.request_id)):
        await ready_lesson(db, user_id, lesson_id)
        sid = _same_request(previous, message)
        return await _replayed_start(db, user_id, sid)
    turn_id = new_id()
    try:
        sid = await runner.start(
            user_id,
            CONVERSATION_GRAPH,
            {"thread_id": thread_id, "turn_id": turn_id},
            subject_type=LESSON_SCOPE,
            subject_id=lesson_id,
            prepare=_reserve(user_id, lesson_id, thread_id, turn_id, message),
        )
    except _RepeatedRequest as repeated:
        return await _replayed_start(db, user_id, repeated.session_id)
    return ConversationStarted.model_validate({"session_id": sid})


async def _replayed_start(db: AsyncSession, user_id: str, sid: str) -> ConversationStarted:
    """Rend le même lancement au MCP joué, si la session appartient bien à ce client."""
    play = PLAY_CONTEXT.get()
    if play is not None and play.user_id == user_id and play.graph == CONVERSATION_GRAPH:
        facts = await session_facts(db, user_id, sid)
        if facts is not None and play.client is not None and facts.played_by == play.client:
            play.started.append(sid)
    return ConversationStarted.model_validate({"session_id": sid})
