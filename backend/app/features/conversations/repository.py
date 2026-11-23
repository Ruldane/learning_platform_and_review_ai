from datetime import datetime

from sqlalchemy import Select, and_, case, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.conversation_port import CONVERSATION_GRAPH
from app.agents.tools.expert_debate_port import EXPERT_GRAPH
from app.db.models.agents import OPEN_SESSION_STATES, AgentSession, LlmCall
from app.db.models.conversations import Conversation, ConversationTurn
from app.db.models.mcp import McpChange
from app.db.models.study import StudySession
from app.db.repository import UserScopedRepository


class ConversationRepository(UserScopedRepository[Conversation]):
    model = Conversation

    async def by_scope(self, scope: str, thread_id: str) -> Conversation | None:
        found = await self.session.execute(self._scoped(scope).where(Conversation.id == thread_id))
        return found.scalar_one_or_none()

    def _scoped(self, scope: str) -> Select[Conversation]:
        return select(Conversation).where(
            Conversation.user_id == self.user_id, Conversation.scope == scope
        )

    async def recent(self, scope: str) -> list[Conversation]:
        return list(
            await self.session.scalars(
                self._scoped(scope).order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            )
        )

    async def preferred(self, scope: str, legacy_id: str) -> Conversation | None:
        found = await self.session.execute(
            self._scoped(scope)
            .order_by(
                (Conversation.id == legacy_id).desc(),
                Conversation.updated_at.desc(),
                Conversation.id.desc(),
            )
            .limit(1)
        )
        return found.scalar_one_or_none()

    async def claim(self, scope: str, thread_id: str | None = None) -> list[Conversation]:
        """Prend le verrou d'écriture SQLite avant de relire les tours du périmètre."""
        stmt = update(Conversation).where(
            Conversation.user_id == self.user_id, Conversation.scope == scope
        )
        if thread_id is not None:
            stmt = stmt.where(Conversation.id == thread_id)
        return list(
            await self.session.scalars(
                stmt.values(updated_at=Conversation.updated_at).returning(Conversation)
            )
        )

    async def cancel_erased_training(self, ids: list[str], now: datetime) -> None:
        await self.session.execute(
            update(StudySession)
            .where(
                StudySession.user_id == self.user_id,
                StudySession.id.in_(ids),
                StudySession.kind == "training",
                StudySession.status == "open",
            )
            .values(status="cancelled", ended_at=now)
        )

    async def erase_chat_snapshots(self, thread_ids: list[str], session_ids: list[str]) -> None:
        # Retire l'appel entier pour que l'annulation ne rejoue jamais une partie de l'écriture.
        snapshots = select(McpChange.call_id).where(
            McpChange.user_id == self.user_id,
            (
                (McpChange.table_name == "conversations") & McpChange.row_id.in_(thread_ids)
                | (McpChange.table_name == "sessions") & McpChange.row_id.in_(session_ids)
                | (McpChange.table_name == "session_events")
                & (
                    McpChange.before["session_id"].as_string().in_(session_ids)
                    | McpChange.after["session_id"].as_string().in_(session_ids)
                )
                | (McpChange.table_name == "conversation_turns")
                & (
                    McpChange.before["thread_id"].as_string().in_(thread_ids)
                    | McpChange.after["thread_id"].as_string().in_(thread_ids)
                )
            ),
        )
        await self.session.execute(
            delete(McpChange).where(
                McpChange.user_id == self.user_id, McpChange.call_id.in_(snapshots)
            )
        )


class TurnRepository(UserScopedRepository[ConversationTurn]):
    model = ConversationTurn

    def __init__(self, session: AsyncSession, user_id: str) -> None:
        super().__init__(session, user_id)
        self._owned_session = and_(
            AgentSession.id == ConversationTurn.session_id, AgentSession.user_id == user_id
        )

    async def by_request(self, thread_id: str, request_id: str) -> ConversationTurn | None:
        return next(iter(await self.list(thread_id=thread_id, request_id=request_id)), None)

    async def used_tokens(self, session_id: str) -> int:
        stmt = select(AgentSession.tokens_in + AgentSession.tokens_out).where(
            AgentSession.id == session_id, AgentSession.user_id == self.user_id
        )
        return int(await self.session.scalar(stmt) or 0)

    async def latest(self, thread_id: str) -> tuple[ConversationTurn, str] | None:
        stmt = (
            select(ConversationTurn, AgentSession.status)
            .join(AgentSession, self._owned_session)
            .where(
                ConversationTurn.thread_id == thread_id, ConversationTurn.user_id == self.user_id
            )
            .order_by(ConversationTurn.created_at.desc(), ConversationTurn.id.desc())
            .limit(1)
        )
        found = (await self.session.execute(stmt)).first()
        return (found[0], found[1]) if found is not None else None

    async def lock_completed(self, turn_id: str) -> ConversationTurn | None:
        completed = select(AgentSession.id).where(
            self._owned_session, AgentSession.status == "completed"
        )
        return await self.session.scalar(
            update(ConversationTurn)
            .where(
                ConversationTurn.id == turn_id,
                ConversationTurn.user_id == self.user_id,
                completed.exists(),
            )
            .values(updated_at=ConversationTurn.updated_at)
            .returning(ConversationTurn)
        )

    async def turns(self, thread_id: str) -> list[tuple[ConversationTurn, str]]:
        stmt = (
            select(ConversationTurn, AgentSession.status)
            .join(AgentSession, self._owned_session)
            .where(
                ConversationTurn.thread_id == thread_id, ConversationTurn.user_id == self.user_id
            )
            .order_by(ConversationTurn.created_at, ConversationTurn.id)
        )
        return [(row, status) for row, status in (await self.session.execute(stmt)).all()]

    async def history(self, turn: ConversationTurn, limit: int) -> list[ConversationTurn]:
        stmt = (
            select(ConversationTurn)
            .join(AgentSession, self._owned_session)
            .where(
                ConversationTurn.user_id == self.user_id,
                ConversationTurn.thread_id == turn.thread_id,
                ConversationTurn.created_at < turn.created_at,
                ConversationTurn.answer.is_not(None),
                AgentSession.status == "completed",
            )
            .order_by(ConversationTurn.created_at.desc(), ConversationTurn.id.desc())
            .limit(limit)
        )
        return list(reversed((await self.session.scalars(stmt)).all()))

    async def usage(
        self, thread_id: str, since: datetime, reserve: int
    ) -> tuple[int, int, int, int]:
        """Jetons du fil et du jour, tours du fil et réserve restante des tours ouverts."""
        in_thread = ConversationTurn.thread_id == thread_id
        open_turn = AgentSession.status.in_(OPEN_SESSION_STATES)
        tokens = AgentSession.tokens_in + AgentSession.tokens_out
        remaining = case((and_(open_turn, tokens < reserve), reserve - tokens), else_=0)
        day_tokens = (
            select(func.coalesce(func.sum(LlmCall.tokens_in + LlmCall.tokens_out), 0))
            .where(
                LlmCall.user_id == self.user_id,
                LlmCall.graph.in_((CONVERSATION_GRAPH, EXPERT_GRAPH)),
                LlmCall.created_at >= since,
            )
            .scalar_subquery()
        )
        stmt = (
            select(
                func.coalesce(func.sum(tokens).filter(in_thread), 0),
                day_tokens,
                func.count().filter(in_thread),
                func.coalesce(func.sum(remaining), 0),
            )
            .select_from(ConversationTurn)
            .join(AgentSession, self._owned_session)
            .where(ConversationTurn.user_id == self.user_id, in_thread | open_turn)
        )
        thread, day, turns, reserved = (await self.session.execute(stmt)).one()
        return int(thread), int(day), int(turns), int(reserved)

    async def claim_reply(
        self, thread_id: str, turn_id: str, session_id: str
    ) -> ConversationTurn | None:
        """Verrou d'écriture SQLite : une annulation MCP et la réponse ne se croisent pas."""
        running = select(AgentSession.id).where(
            self._owned_session, AgentSession.status == "running"
        )

        return await self.session.scalar(
            update(ConversationTurn)
            .where(
                ConversationTurn.user_id == self.user_id,
                ConversationTurn.id == turn_id,
                ConversationTurn.thread_id == thread_id,
                ConversationTurn.session_id == session_id,
                ConversationTurn.answer.is_(None),
                running.exists(),
            )
            .values(updated_at=ConversationTurn.updated_at)
            .returning(ConversationTurn)
        )

    async def cancel_open(self, thread_id: str) -> str | None:
        sessions = select(ConversationTurn.session_id).where(
            ConversationTurn.thread_id == thread_id, ConversationTurn.user_id == self.user_id
        )
        return await self.session.scalar(
            update(AgentSession)
            .where(
                AgentSession.user_id == self.user_id,
                AgentSession.id.in_(sessions),
                AgentSession.status.in_(OPEN_SESSION_STATES),
            )
            .values(status="cancelled", pending_interrupt=None)
            .returning(AgentSession.id)
        )

    async def erase_sessions(self, ids: list[str]) -> None:
        # Les événements et les échanges sont effacés par les clés étrangères.
        await self.session.execute(
            delete(AgentSession).where(
                AgentSession.user_id == self.user_id, AgentSession.id.in_(ids)
            )
        )
