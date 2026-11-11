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

    async def read_status() -> str:
        try:
            return (await control.get_owned(factory, user_id, session_id)).status
        except AppError:
            return "cancelled"  # session disparue : plus rien à attendre

    async def read_last_seq() -> int:
        async with factory() as db:
            return await EventRepository(db, user_id).max_seq(session_id)

    await replay.stream_to_socket(
        ws,
        runtime.bus,
        user_id,
        session_id,
        after_seq,
        read_status=read_status,
        read_last_seq=read_last_seq,
    )
