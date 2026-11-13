"""Sessions d'agents côté API : lectures par le repository de la feature, actions par le runner
(qui ouvre ses propres sessions de base courtes et applique les règles de statut, D46)."""

import builtins
from dataclasses import dataclass
from typing import Any

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
from app.features.sessions.schemas import (
    MessageRequest,
    ResumeRequest,
    SessionView,
    StartSessionRequest,
)

# Les autres features passent par ce service (contrat 2) : requêtes et vue réexportées.
__all__ = [
    "MessageRequest",
    "ResumeRequest",
    "SessionFacts",
    "SessionView",
    "SessionsService",
    "find_active_session",
    "find_latest_session",
    "list_open_sessions",
    "list_open_sessions_by_subject",
    "session_facts",
    "to_view",
]


# Parcours lancés seulement par la route de leur feature, qui vérifie l'objet et la concurrence
# (D106 : une replanification par programme, programme validé ; 409 `replan_open` ; quiz et
# séance : verrou, sujet et ligne de la feature, revue finale de la phase 5).
ROUTE_ONLY: dict[str, str] = {
    "replan": "POST /programs/{program_id}/replan",
    "capture": "POST /capture",
    "quiz": "POST /modules/{module_id}/quiz",
    "study_session": "POST /study-sessions",
}


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


async def list_open_sessions(
    db: AsyncSession, user_id: str, *, graph: str, subject_type: str, subject_id: str
) -> builtins.list[str]:
    """Toutes les sessions ouvertes de `graph` sur cet objet (production des leçons : une chaîne
    par programme, D91). Lecture pour les autres features (contrat 2)."""
    return await SessionReadRepository(db, user_id).open_ids(
        graph=graph, subject_type=subject_type, subject_id=subject_id
    )


async def list_open_sessions_by_subject(
    db: AsyncSession, user_id: str, *, graph: str, subject_type: str
) -> builtins.dict[str, builtins.list[str]]:
    """Sessions ouvertes de `graph` sur tous les objets d'un type, par `subject_id`, en une
    requête (listes sans N+1). Lecture pour les autres features (contrat 2)."""
    return await SessionReadRepository(db, user_id).open_ids_by_subject(
        graph=graph, subject_type=subject_type
    )


async def find_latest_session(
    db: AsyncSession, user_id: str, *, graph: str, subject_type: str, subject_id: str
) -> str | None:
    """Session la plus récente de `graph` sur cet objet, quel que soit son statut, `None` s'il
    n'y en a pas. Lecture pour les autres features (contrat 2)."""
    return await SessionReadRepository(db, user_id).latest(
        graph=graph, subject_type=subject_type, subject_id=subject_id
    )


@dataclass(frozen=True)
class SessionFacts:
    status: str
    input: dict[str, Any]


async def session_facts(db: AsyncSession, user_id: str, session_id: str) -> SessionFacts | None:
    """Statut et entrée d'une session de l'utilisateur (relance d'un parcours en échec, D97),
    `None` si elle n'existe pas. Lecture pour les autres features (contrat 2)."""
    row = await SessionReadRepository(db, user_id).get(session_id)
    return None if row is None else SessionFacts(row.status, dict(row.input or {}))


class SessionsService:
    def __init__(self, db: AsyncSession, user_id: str, runtime: AgentRuntime) -> None:
        self._repo = SessionReadRepository(db, user_id)
        self._user_id = user_id
        self._runner = runtime.runner

    async def start(self, req: StartSessionRequest) -> str:
        """Crée la session et lance le parcours en tâche de fond : rend la main aussitôt. Un
        parcours qui a sa propre route (`ROUTE_ONLY`) y est renvoyé (409 `graph_has_route`)."""
        if req.graph in ROUTE_ONLY:
            raise AppError(
                "graph_has_route",
                "Ce parcours se lance depuis son écran.",
                409,
                {"graph": req.graph, "route": ROUTE_ONLY[req.graph]},
            )
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

    async def message(self, session_id: str, req: MessageRequest) -> SessionEvent:
        """Publie le message (texte sans blancs autour) et sa commande ; rien à dire ni à
        commander : 422, chemin `text` seul, jamais la saisie."""
        text = req.text.strip()
        if not text and req.command is None:
            raise AppError(
                "invalid_input",
                "Écris un message ou choisis une commande.",
                422,
                {"fields": ["text"]},
            )
        return await self._runner.post_message(self._user_id, session_id, text, req.command)

    async def pause(self, session_id: str) -> SessionView:
        await self._runner.pause(self._user_id, session_id)
        return await self.get(session_id)

    async def cancel(self, session_id: str) -> SessionView:
        await self._runner.cancel(self._user_id, session_id)
        return await self.get(session_id)
