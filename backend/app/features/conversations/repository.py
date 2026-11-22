from datetime import datetime

from sqlalchemy import and_, case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.conversation_port import CONVERSATION_GRAPH
from app.db.models.agents import OPEN_SESSION_STATES, AgentSession, LlmCall
from app.db.models.conversations import Conversation, ConversationTurn
from app.db.repository import UserScopedRepository


class ConversationRepository(UserScopedRepository[Conversation]):
    model = Conversation


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
                LlmCall.graph == CONVERSATION_GRAPH,
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
