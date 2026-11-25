"""From the bus to the WebSocket: replay after `after_seq`, then live, until the end of the session
or
the client's disconnection. The stream goes only from the server to the client (SPEC 14.1):
received messages are ignored; we only listen for the disconnection.

Three tasks in an anyio group (structured cancellation: nothing survives the connection, even when
the server cancels the handler): `forward` (bus → socket), `listen` (disconnection), `watch`
(session cancelled). The first to conclude cancels the others; cancelled while waiting, the bus
generator receives the cancellation and unregisters its queue.

End of the stream, always deterministic (never inferred from silence: a slow client must not receive
a 1000 in the middle of the replay):
- `run.completed` / `run.failed` sent: these are always the last events of a `completed` / `failed`
  session (D46); `forward` closes at once (code 1000).
- the bus ends the subscription (`close` on a terminal status, D42) → 1000.
- a subscriber arriving after that `close` (or a client coming back with `after_seq` beyond the
end):
  the bus replays, then waits indefinitely. Once the subscription is registered, `watch` reads the
  end `seq` ONCE (`read_end_seq`): that of `run.completed` / `run.failed` if it is written, the last
  `seq` of a `cancelled` session (no final event), `None` for an open session. The final status and
  the final event are written together (D61): a `completed` / `failed` session always has its end
  `seq`.
  It closes when `forward` has sent up to that `seq` and waits on the bus: at once if `after_seq`
  already reaches it.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import aclosing, suppress
from dataclasses import dataclass, field

import anyio
from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

from app.agents.runtime.bus import EventBus
from app.agents.runtime.events import SessionEvent

FINAL_EVENTS = frozenset({"run.completed", "run.failed"})

# `seq` after which the session will write nothing more, `None` if it can still write.
type EndSeqReader = Callable[[], Awaitable[int | None]]


@dataclass
class _Stream:
    sent_seq: int  # last `seq` sent (at the start: `after_seq`)
    waiting: bool = False  # `forward` waits for the bus (no send in progress)
    finished: bool = False  # session over: the server closes the socket
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
    """Sends each `SessionEvent` as JSON (`model_dump(mode="json")`) until the client disconnects,
    or
    until the end of the session (the server then closes with 1000)."""
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
        with suppress(WebSocketDisconnect, RuntimeError):  # client left in the meantime
            await ws.close(code=1000)


async def _forward(ws: WebSocket, events: AsyncIterator[SessionEvent], stream: _Stream) -> bool:
    """Forwards the events; `True` if the session is over, `False` if the client left during a
    send."""
    while True:
        stream.waiting = True
        await stream.notify()
        pending = anext(events, None)
        # The first step of `anext` registers the subscriber's queue before any wait (D42):
        # signalled before, `watch` runs only once that step is done.
        stream.subscribed.set()
        event = await pending
        stream.waiting = False
        if event is None:
            return True  # subscription ended by the bus: session closed
        try:
            await ws.send_json(event.model_dump(mode="json"))
        except WebSocketDisconnect:
            return False
        stream.sent_seq = event.seq
        if event.type in FINAL_EVENTS:
            return True


async def _drained(read_end_seq: EndSeqReader, stream: _Stream) -> None:
    """Returns control when the session is over and everything up to its end has been sent;
    otherwise
    waits indefinitely (the final event or the bus's `close` will conclude)."""
    await stream.subscribed.wait()
    # Read AFTER the registration: if the session can still write, what it will write (final event,
    # bus `close`) will find this subscriber.
    end = await read_end_seq()
    if end is None:
        await anyio.sleep_forever()
        return
    async with stream.changed:
        while not (stream.waiting and stream.sent_seq >= end):
            await stream.changed.wait()


async def _until_disconnect(ws: WebSocket) -> None:
    """Reads (and ignores) the client's messages until it disconnects."""
    while True:
        message = await ws.receive()
        if message["type"] == "websocket.disconnect":
            return
