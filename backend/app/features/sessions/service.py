"""Sessions d'agents côté API : lectures par le repository de la feature, actions par le runner
(qui ouvre ses propres sessions de base courtes et applique les règles de statut, D46)."""

import builtins

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.events import (
    InterruptRequestedPayload,
    RunFailedPayload,
    SessionEvent,
)
from app.agents.runtime.handle import AgentRuntime
from app.core.errors import AppError
from app.db.models.agents import AgentSession, SessionStatus
from app.features.sessions.repository import SessionReadRepository
from app.features.sessions.schemas import ResumeRequest, SessionView, StartSessionRequest


def to_view(row: AgentSession, last_seq: int) -> SessionView:
    pending = row.pending_interrupt
    return SessionView(
        id=row.id,
        graph=row.graph,
        status=row.status,  # type: ignore[arg-type]  # colonne texte, valeurs de SessionStatus
        subject_type=row.subject_type,
        subject_id=row.subject_id,
        last_seq=last_seq,
        pending_interrupt=InterruptRequestedPayload.model_validate(pending) if pending else None,
        error=RunFailedPayload.model_validate(row.error) if row.error else None,
        tokens_in=row.tokens_in,
        tokens_out=row.tokens_out,
        cost_usd=row.cost_usd,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def find_active_session(
    db: AsyncSession, user_id: str, *, graph: str, subject_type: str, subject_id: str
) -> str | None:
    """Session la plus récente de `graph` sur cet objet encore ouverte (`running`,
    `waiting_user` ou `paused`), `None` sinon. Lecture pour les autres features (contrat 2)."""
    return await SessionReadRepository(db, user_id).latest_open(
        graph=graph, subject_type=subject_type, subject_id=subject_id
    )


class SessionsService:
    def __init__(self, db: AsyncSession, user_id: str, runtime: AgentRuntime) -> None:
        self._repo = SessionReadRepository(db, user_id)
        self._user_id = user_id
        self._runner = runtime.runner

    async def start(self, req: StartSessionRequest) -> str:
        """Crée la session et lance le parcours en tâche de fond : rend la main aussitôt."""
        return await self._runner.start(
            self._user_id, req.graph, req.input, req.subject_type, req.subject_id
        )

    async def get(self, session_id: str) -> SessionView:
        """Le dernier `seq` est lu AVANT la ligne : le statut rendu est donc au moins aussi
        récent que `last_seq`, et le front peut ordonner cette lecture et les événements (D56)."""
        seqs = await self._repo.last_seqs([session_id])
        row = await self._repo.get(session_id)
        if row is None:
            raise AppError("session_not_found", "Session introuvable.", 404)
        return to_view(row, seqs.get(session_id, 0))

    async def list(
        self, graph: str | None, status: SessionStatus | None
    ) -> builtins.list[SessionView]:
        rows = await self._repo.list_recent(graph=graph, status=status)
        seqs = await self._repo.last_seqs([row.id for row in rows])
        return [to_view(row, seqs.get(row.id, 0)) for row in rows]

    async def resume(self, session_id: str, req: ResumeRequest) -> SessionView:
        await self._runner.resume(self._user_id, session_id, req.interrupt_id, req.value)
        return await self.get(session_id)

    async def message(self, session_id: str, text: str) -> SessionEvent:
        return await self._runner.post_message(self._user_id, session_id, text)

    async def pause(self, session_id: str) -> SessionView:
        await self._runner.pause(self._user_id, session_id)
        return await self.get(session_id)

    async def cancel(self, session_id: str) -> SessionView:
        await self._runner.cancel(self._user_id, session_id)
        return await self.get(session_id)
