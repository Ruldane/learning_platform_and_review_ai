"""Point d'entrée WebSocket du flux d'une session : origine, propriété, puis rejeu et direct.

- **Origine** : CORS ne s'applique pas aux WebSockets ; un navigateur envoie toujours `Origin`,
  qui doit être l'une des origines autorisées (`Settings.cors_origins`), sinon la poignée de
  main est refusée (fermeture 1008 avant `accept` : le navigateur, lui, ne voit qu'un 1006,
  comme pour un `after_seq` invalide ou un 401). Sans en-tête `Origin` (client hors
  navigateur, tests), accepté.
- **Propriété** : session inconnue ou d'un autre utilisateur → accepté puis fermé en `4404`
  (un refus avant `accept` n'arriverait au navigateur que comme un 1006 anonyme).
- **Base** : jamais de session ouverte pour la durée de la connexion (D38) ; chaque lecture
  (propriété, statut, dernier `seq`) ouvre une session courte par `session_factory`.
"""

from fastapi import WebSocketException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.requests import HTTPConnection
from starlette.websockets import WebSocket

from app.agents.runtime import control
from app.agents.runtime.handle import AgentRuntime
from app.agents.runtime.repositories import EventRepository
from app.core.errors import AppError
from app.realtime import replay

CLOSE_NOT_FOUND = 4404


def check_origin(conn: HTTPConnection) -> None:
    """Dépendance de la route WebSocket : refuse une origine hors de `cors_origins`."""
    origin = conn.headers.get("origin")
    if origin is None:
        return
    if origin.rstrip("/") not in conn.app.state.settings.cors_origins:
        raise WebSocketException(status.WS_1008_POLICY_VIOLATION, "Origine non autorisée.")


async def serve_session_stream(
    ws: WebSocket, runtime: AgentRuntime, user_id: str, session_id: str, after_seq: int
) -> None:
    factory: async_sessionmaker[AsyncSession] = ws.app.state.session_factory
    await ws.accept()
    try:
        await control.get_owned(factory, user_id, session_id)
    except AppError:
        await ws.close(code=CLOSE_NOT_FOUND, reason="Session introuvable.")
        return

    await replay.stream_to_socket(
        ws,
        runtime.bus,
        user_id,
        session_id,
        after_seq,
        read_end_seq=end_seq_reader(factory, user_id, session_id),
    )


def end_seq_reader(
    factory: async_sessionmaker[AsyncSession], user_id: str, session_id: str
) -> replay.EndSeqReader:
    """`seq` de fin de la session (voir `replay`) : statut lu d'abord, puis le `seq` dans une
    autre session courte, pour qu'il soit au moins aussi récent que le statut."""

    async def read() -> int | None:
        try:
            status = (await control.get_owned(factory, user_id, session_id)).status
        except AppError:
            return 0  # session disparue : plus rien à attendre
        if status not in control.TERMINAL:
            return None
        async with factory() as db:
            events = EventRepository(db, user_id)
            if status == "cancelled":  # aucun événement final : tout ce qui est écrit
                return await events.max_seq(session_id)
            # `completed` / `failed` : l'événement final, écrit dans la même transaction que
            # le statut (D61). `None` (ligne d'avant D61 sans son événement) : flux ouvert.
            return await events.last_seq_of(session_id, replay.FINAL_EVENTS)

    return read
