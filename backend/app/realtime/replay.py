"""Du bus au WebSocket : rejeu après `after_seq`, puis direct, jusqu'à la fin de la session ou la
déconnexion du client. Le flux ne va que du serveur vers le client (SPEC 14.1) : les messages
reçus sont ignorés, on n'écoute que la déconnexion.

Trois tâches dans un groupe anyio (annulation structurée : rien ne survit à la connexion, même
quand le serveur annule le gestionnaire) : `forward` (bus → socket), `listen` (déconnexion),
`watch` (fin silencieuse). La première qui conclut annule les autres ; annulé pendant son
attente, le générateur du bus reçoit l'annulation et désinscrit sa file.

Fin du flux :
- `run.completed` / `run.failed` transmis : ce sont toujours les derniers événements d'une
  session (statuts terminaux, D46) ; le serveur ferme aussitôt (code 1000).
- le bus termine l'abonnement (`close` sur un statut terminal, D42).
- abonné arrivé après ce `close` (session annulée, par exemple) : le bus rejoue puis attend
  indéfiniment. Après un premier silence de `IDLE_CHECK_S`, l'abonnement est forcément inscrit :
  `watch` lit alors le statut, une seule fois. Non terminal → le `close` à venir terminera
  l'abonnement. Terminal → encore un silence (un `run.completed` en cours d'écriture arriverait
  entre-temps), puis fermeture.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import aclosing, suppress
from dataclasses import dataclass

import anyio
from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

from app.agents.runtime.bus import EventBus
from app.agents.runtime.events import SessionEvent

IDLE_CHECK_S = 1.0
TERMINAL = frozenset({"completed", "failed", "cancelled"})
FINAL_EVENTS = frozenset({"run.completed", "run.failed"})

type StatusReader = Callable[[], Awaitable[str]]


@dataclass
class _Stream:
    sent: int = 0  # événements transmis (mesure des silences)
    finished: bool = False  # session finie : le serveur ferme le socket


async def stream_to_socket(
    ws: WebSocket,
    bus: EventBus,
    user_id: str,
    session_id: str,
    after_seq: int,
    *,
    read_status: StatusReader,
) -> None:
    """Envoie chaque `SessionEvent` en JSON (`model_dump(mode="json")`) jusqu'à la déconnexion
    du client, ou jusqu'à la fin de la session (le serveur ferme alors en 1000)."""
    stream = _Stream()
    subscription = bus.subscribe(user_id=user_id, session_id=session_id, after_seq=after_seq)
    async with aclosing(subscription) as events, anyio.create_task_group() as tg:

        async def forward() -> None:
            stream.finished = await _forward(ws, events, stream)
            tg.cancel_scope.cancel()

        async def listen() -> None:
            await _until_disconnect(ws)
            tg.cancel_scope.cancel()

        async def watch() -> None:
            await _ended_quietly(read_status, stream)
            stream.finished = True
            tg.cancel_scope.cancel()

        tg.start_soon(forward)
        tg.start_soon(listen)
        tg.start_soon(watch)
    if stream.finished and ws.application_state == WebSocketState.CONNECTED:
        with suppress(WebSocketDisconnect, RuntimeError):  # client parti entre-temps
            await ws.close(code=1000)


async def _forward(ws: WebSocket, events: AsyncIterator[SessionEvent], stream: _Stream) -> bool:
    """Transmet les événements ; `True` si la session est finie, `False` si le client est
    parti pendant un envoi."""
    async for event in events:
        try:
            await ws.send_json(event.model_dump(mode="json"))
        except WebSocketDisconnect:
            return False
        stream.sent += 1
        if event.type in FINAL_EVENTS:
            return True
    return True  # abonnement terminé par le bus : session fermée


async def _ended_quietly(read_status: StatusReader, stream: _Stream) -> None:
    """Rend la main quand la session est terminée sans que le bus ne termine l'abonnement
    (abonné arrivé après `close`) ; sinon attend indéfiniment (annulé par les autres tâches)."""
    await _silence(stream)
    if await read_status() not in TERMINAL:
        await anyio.sleep_forever()  # le `close` du bus terminera l'abonnement
    await _silence(stream)


async def _silence(stream: _Stream) -> None:
    """Attend une période complète de `IDLE_CHECK_S` sans aucun événement transmis."""
    while True:
        seen = stream.sent
        await anyio.sleep(IDLE_CHECK_S)
        if stream.sent == seen:
            return


async def _until_disconnect(ws: WebSocket) -> None:
    """Lit (et ignore) les messages du client jusqu'à sa déconnexion."""
    while True:
        message = await ws.receive()
        if message["type"] == "websocket.disconnect":
            return
