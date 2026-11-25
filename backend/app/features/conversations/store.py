from collections.abc import Sequence
from contextlib import nullcontext
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.conversation_port import (
    BRAIN_LIBRARIAN,
    CLASSROOM_SCOPE,
    LESSON_PROFESSOR,
    OFFERS_ADVISER,
    TRAINING_TUTOR,
    ClassmateReply,
    ConversationContext,
    ConversationExchange,
    ConversationPractice,
    ConversationReference,
    ConversationSource,
    FocusOutcome,
)
from app.agents.tools.feynman_port import (
    FEYNMAN_SCOPES,
    FeynmanAssessment,
    FeynmanContext,
    FeynmanExchange,
)
from app.core.errors import AppError
from app.db.models.conversations import Conversation, ConversationTurn
from app.features.brain.service.reading import active_note_versions, matching_notes
from app.features.conversations.feynman_schemas import FeynmanData, FeynmanReport
from app.features.conversations.feynman_source import material
from app.features.conversations.lesson_context import (
    lesson_excerpt,
    lesson_material,
    ready_lesson,
    require_current_version,
)
from app.features.conversations.offers import OFFERS_SCOPE
from app.features.conversations.offers_context import offers_references
from app.features.conversations.repository import ConversationRepository, TurnRepository
from app.features.conversations.service import BRAIN_SCOPE, LESSON_SCOPE, TRAINING_SCOPE
from app.features.conversations.training_context import selected_refs
from app.features.lessons.service.conversation import lesson_terms, search_published
from app.mcp.recorder import ChangeRecorder

MAX_HISTORY = 4
MAX_HISTORY_FIELD = 800


async def _owned_turn(
    repo: TurnRepository, session_id: str, thread_id: str, turn_id: str
) -> tuple[Conversation, ConversationTurn]:
    turn = await repo.get(turn_id)
    thread = await ConversationRepository(repo.session, repo.user_id).get(thread_id)
    if (
        turn is None
        or thread is None
        or turn.thread_id != thread_id
        or turn.session_id != session_id
    ):
        raise AppError("conversation_turn_not_found", "Conversation turn not found.", 404)
    return thread, turn


async def _lesson_refs(
    db: AsyncSession,
    thread: Conversation,
    turn: ConversationTurn,
) -> list[ConversationReference]:
    title, markdown = await ready_lesson(db, thread.user_id, thread.subject_id)
    require_current_version(markdown, turn)
    source = ConversationSource(
        kind="lesson", id=UUID(thread.subject_id), title=title, excerpt=turn.passage
    )
    return [
        ConversationReference(
            source, lesson_material(markdown, turn.passage, turn.passage_occurrence), primary=True
        )
    ]


async def _published_refs(
    db: AsyncSession,
    turn: ConversationTurn,
    history: list[ConversationTurn],
    *,
    followed_only: bool = False,
) -> list[ConversationReference]:
    previous = list(
        dict.fromkeys(
            str(source["id"])
            for past in reversed(history)
            for source in past.sources
            if source["kind"] == "lesson"
        )
    )
    terms = lesson_terms(turn.question)
    out = []
    for found in await search_published(
        db,
        turn.user_id,
        terms,
        previous,
        followed_only=followed_only,
    ):
        material = lesson_excerpt(found.markdown, terms)
        out.append(
            ConversationReference(
                ConversationSource(
                    kind="lesson", id=UUID(found.id), title=found.title, excerpt=material[:400]
                ),
                material,
                primary=True,
            )
        )
    return out


async def _brain_context(
    db: AsyncSession, turn: ConversationTurn, history: list[ConversationTurn]
) -> tuple[list[ConversationTurn], list[ConversationReference], dict[str, str]]:
    """An exchange depends on every note given to its model, even without a citation."""
    prior_ids = {item_id for past in history for item_id in past.context_notes or {}}
    live = await active_note_versions(db, turn.user_id, prior_ids)
    safe = [
        past
        for past in history
        if past.context_notes is not None
        and all(live.get(item_id) == version for item_id, version in past.context_notes.items())
    ]
    notes = await matching_notes(db, turn.user_id, lesson_terms(turn.question))
    references = [
        ConversationReference(
            ConversationSource(
                kind="memory", id=UUID(note.item_id), title=note.title, excerpt=note.material[:400]
            ),
            note.material,
            primary=True,
        )
        for note in notes
    ]
    versions = {
        item_id: version for past in safe for item_id, version in (past.context_notes or {}).items()
    }
    versions.update((note.item_id, note.version) for note in notes)
    references.extend(await _published_refs(db, turn, safe, followed_only=True))
    return safe, references, versions


def _exchange(row: ConversationTurn) -> ConversationExchange:
    if row.classmates:
        replies = [ClassmateReply.model_validate(reply) for reply in row.classmates]
        answer = " | ".join(f"{reply.role} : {reply.answer[:130]}" for reply in replies)
        return ConversationExchange(row.question[:210], answer)
    return ConversationExchange(
        row.question[:MAX_HISTORY_FIELD], (row.answer or "")[:MAX_HISTORY_FIELD]
    )


class AgentConversationStore:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def feynman_context(
        self, user_id: str, session_id: str, thread_id: str, turn_id: str
    ) -> FeynmanContext | None:
        async with self._factory() as db:
            repo = TurnRepository(db, user_id)
            thread, turn = await _owned_turn(repo, session_id, thread_id, turn_id)
            if turn.answer is not None:
                return None
            if thread.scope not in FEYNMAN_SCOPES or turn.feynman is None:
                raise AppError("feynman_not_found", "Explanation not found.", 404)
            data = FeynmanData.model_validate(turn.feynman)
            text = await material(db, user_id, data.source, turn.lesson_version)
            title = data.source.path or data.source.title
            return FeynmanContext(title, text, turn.strong, await repo.used_tokens(session_id))

    async def save_feynman(
        self,
        user_id: str,
        session_id: str,
        thread_id: str,
        turn_id: str,
        *,
        assessment: FeynmanAssessment,
        exchange: FeynmanExchange,
    ) -> None:
        async with self._factory() as db:
            turn = await TurnRepository(db, user_id).claim_reply(thread_id, turn_id, session_id)
            if turn is None:
                return
            data = FeynmanData.model_validate(turn.feynman)
            await material(db, user_id, data.source, turn.lesson_version)
            data.report = FeynmanReport(
                **exchange.model_dump(),
                summary=assessment.summary,
                cards=assessment.cards,
                proof_skill=data.skill if assessment.mastered else None,
            )
            turn.feynman = data.model_dump(mode="json")
            turn.answer = assessment.summary
            await db.commit()

    async def context(
        self, user_id: str, session_id: str, thread_id: str, turn_id: str
    ) -> ConversationContext | None:
        async with self._factory() as db:
            repo = TurnRepository(db, user_id)
            thread, turn = await _owned_turn(repo, session_id, thread_id, turn_id)
            if turn.answer is not None:
                return None
            history = await repo.history(turn, MAX_HISTORY)
            notes: dict[str, str] | None = None
            if thread.scope == LESSON_SCOPE:
                agent, refs = LESSON_PROFESSOR, await _lesson_refs(db, thread, turn)
            elif thread.scope == CLASSROOM_SCOPE:
                agent, refs = TRAINING_TUTOR, await _lesson_refs(db, thread, turn)
            elif thread.scope == TRAINING_SCOPE:
                agent = TRAINING_TUTOR
                refs = (
                    await selected_refs(db, turn)
                    if turn.lesson_ids
                    else await _published_refs(db, turn, history)
                )
            elif thread.scope == BRAIN_SCOPE:
                agent = BRAIN_LIBRARIAN
                history, refs, notes = await _brain_context(db, turn, history)
            elif thread.scope == OFFERS_SCOPE:
                agent, refs = OFFERS_ADVISER, await offers_references(db, turn, history)
            else:
                raise AppError(
                    "conversation_scope_unknown", "This thread type is unavailable.", 409
                )
            used = await repo.used_tokens(session_id)
        exchanges = [_exchange(row) for row in history if row.answer is not None]
        return ConversationContext(
            agent,
            turn.question,
            turn.strong,
            exchanges,
            refs,
            used,
            selection=turn.passage,
            mode=turn.mode,
            context_notes=notes,
        )

    async def save_reply(
        self,
        user_id: str,
        session_id: str,
        thread_id: str,
        turn_id: str,
        *,
        answer: str,
        sources: Sequence[ConversationSource],
        practice: Sequence[ConversationPractice] = (),
        context_notes: dict[str, str] | None = None,
        classmates: Sequence[ClassmateReply] = (),
        focus_outcome: FocusOutcome | None = None,
    ) -> None:
        async with self._factory() as db:
            repo = TurnRepository(db, user_id)
            turn = await repo.claim_reply(thread_id, turn_id, session_id)
            if turn is None:
                return
            if turn.lesson_version is not None:
                thread, _ = await _owned_turn(repo, session_id, thread_id, turn_id)
                _, markdown = await ready_lesson(db, user_id, thread.subject_id)
                require_current_version(markdown, turn)
            if (
                context_notes
                and await active_note_versions(db, user_id, context_notes) != context_notes
            ):
                raise AppError(
                    "brain_sources_changed",
                    "Some notes changed during the reply. You can ask your question again.",
                    409,
                )
            recorder = (
                ChangeRecorder(self._factory, turn.mcp_call_id, user_id)
                if turn.mcp_call_id is not None
                else None
            )
            async with recorder if recorder is not None else nullcontext():
                turn.answer = answer
                turn.focus_outcome = focus_outcome
                turn.sources = [source.model_dump(mode="json") for source in sources]
                if practice:
                    turn.practice = [card.model_dump(mode="json") for card in practice]
                turn.context_notes = context_notes
                if classmates:
                    turn.classmates = [reply.model_dump(mode="json") for reply in classmates]
                if recorder is not None:
                    await recorder.extend_in(db, keep_latest=frozenset())
            await db.commit()
