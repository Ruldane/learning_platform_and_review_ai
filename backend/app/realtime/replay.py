"""Du bus au WebSocket : rejeu après `after_seq`, puis direct, jusqu'à la fin de la session ou la
déconnexion du client. Le flux ne va que du serveur vers le client (SPEC 14.1) : les messages
reçus sont ignorés, on n'écoute que la déconnexion.

Trois tâches dans un groupe anyio (annulation structurée : rien ne survit à la connexion, même
quand le serveur annule le gestionnaire) : `forward` (bus → socket), `listen` (déconnexion),
`watch` (session annulée). La première qui conclut annule les autres ; annulé pendant son
attente, le générateur du bus reçoit l'annulation et désinscrit sa file.

Fin du flux, toujours déterministe (jamais déduite d'un silence : un client lent ne doit pas
recevoir un 1000 au milieu du rejeu) :
- `run.completed` / `run.failed` transmis : ce sont toujours les derniers événements d'une
  session `completed` / `failed` (D46) ; `forward` ferme aussitôt (code 1000).
- le bus termine l'abonnement (`close` sur un statut terminal, D42) → 1000.
- abonné arrivé après ce `close` (ou client qui revient avec `after_seq` au-delà de la fin) :
  le bus rejoue puis attend indéfiniment. Une fois l'abonnement inscrit, `watch` lit UNE fois
  le `seq` de fin (`read_end_seq`) : celui de `run.completed` / `run.failed` s'il est écrit, le
  dernier `seq` d'une session `cancelled` (aucun événement final), `None` pour une session
  ouverte. Statut final et événement final sont écrits ensemble (D61) : une session
  `completed` / `failed` a toujours son `seq` de fin.
  Il ferme quand `forward` a transmis jusqu'à ce `seq` et attend le bus — aussitôt si
  `after_seq` l'atteint déjà.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import aclosing, suppress
from dataclasses import dataclass, field

import anyio
from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

from app.agents.runtime.bus import EventBus
from app.agents.runtime.events import SessionEvent

FINAL_EVENTS = frozenset({"run.completed", "run.failed"})

# `seq` après lequel la session n'écrira plus rien, `None` si elle peut encore écrire.
type EndSeqReader = Callable[[], Awaitable[int | None]]


@dataclass
class _Stream:
    sent_seq: int  # dernier `seq` transmis (au départ : `after_seq`)
    waiting: bool = False  # `forward` attend le bus (aucun envoi en cours)
    finished: bool = False  # session finie : le serveur ferme le socket
    subscribed: anyio.Event = field(default_factory=anyio.Event)
    changed: anyio.Condition = field(default_factory=anyio.Condition)

    async def notify(self) -> None:
        async with self.changed:
            self.changed.notify_all()


async def stream_to_socket(
    ws: WebSocket,
    bus: EventBus,
    user_id: str,
    session_id: str,
    after_seq: int,
    *,
    read_end_seq: EndSeqReader,
) -> None:
    """Envoie chaque `SessionEvent` en JSON (`model_dump(mode="json")`) jusqu'à la déconnexion
    du client, ou jusqu'à la fin de la session (le serveur ferme alors en 1000)."""
    stream = _Stream(sent_seq=after_seq)
    subscription = bus.subscribe(user_id=user_id, session_id=session_id, after_seq=after_seq)
    async with aclosing(subscription) as events, anyio.create_task_group() as tg:

        async def forward() -> None:
            stream.finished = await _forward(ws, events, stream)
            tg.cancel_scope.cancel()

        async def listen() -> None:
            await _until_disconnect(ws)
            tg.cancel_scope.cancel()

        async def watch() -> None:
            await _drained(read_end_seq, stream)
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
    while True:
        stream.waiting = True
        await stream.notify()
        pending = anext(events, None)
        # Le premier pas de `anext` inscrit la file de l'abonné avant toute attente (D42) :
        # signalé avant, `watch` ne s'exécute qu'une fois ce pas fait.
        stream.subscribed.set()
        event = await pending
        stream.waiting = False
        if event is None:
            return True  # abonnement terminé par le bus : session fermée
        try:
            await ws.send_json(event.model_dump(mode="json"))
        except WebSocketDisconnect:
            return False
        stream.sent_seq = event.seq
        if event.type in FINAL_EVENTS:
            return True


async def _drained(read_end_seq: EndSeqReader, stream: _Stream) -> None:
    """Rend la main quand la session est finie et que tout jusqu'à sa fin est transmis ;
    sinon attend indéfiniment (l'événement final ou le `close` du bus concluront)."""
    await stream.subscribed.wait()
    # Lu APRÈS l'inscription : si la session peut encore écrire, ce qu'elle écrira (événement
    # final, `close` du bus) trouvera cet abonné.
    end = await read_end_seq()
    if end is None:
        await anyio.sleep_forever()
        return
    async with stream.changed:
        while not (stream.waiting and stream.sent_seq >= end):
            await stream.changed.wait()


async def _until_disconnect(ws: WebSocket) -> None:
    """Lit (et ignore) les messages du client jusqu'à sa déconnexion."""
    while True:
        message = await ws.receive()
        if message["type"] == "websocket.disconnect":
            return
