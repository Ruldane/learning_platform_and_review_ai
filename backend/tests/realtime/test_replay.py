"""`stream_to_socket` sur un vrai bus et un faux socket : la fin du flux est déterministe
(jamais déduite d'un silence), même quand le client lit lentement."""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.websockets import WebSocketState

import app.db.models  # noqa: F401  (enregistre les modèles sur Base.metadata)
from app.agents.runtime.bus import EventBus
from app.agents.runtime.repositories import EventRepository, SessionRepository
from app.db.base import Base, new_id
from app.db.engine import create_engine, create_session_factory
from app.db.models.agents import AgentSession
from app.realtime import replay

pytestmark = pytest.mark.timeout(10)

type Factory = async_sessionmaker[AsyncSession]
USER = new_id()


class FakeSocket:
    """Enregistre les envois et la fermeture ; `pauses[n]` : le n-ième envoi (1-based) reste
    bloqué ce nombre de secondes (client lent, contre-pression TCP)."""

    def __init__(self, pauses: dict[int, float] | None = None) -> None:
        self.sent: list[dict[str, Any]] = []
        self.closed: int | None = None
        self.sent_before_close: int | None = None
        self.pauses = pauses or {}
        self.gone = asyncio.Event()
        self.application_state = WebSocketState.CONNECTED

    async def send_json(self, data: dict[str, Any]) -> None:
        await asyncio.sleep(self.pauses.get(len(self.sent) + 1, 0))
        self.sent.append(data)

    async def receive(self) -> dict[str, Any]:
        await self.gone.wait()
        return {"type": "websocket.disconnect", "code": 1000}

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        self.closed, self.sent_before_close = code, len(self.sent)
        self.application_state = WebSocketState.DISCONNECTED

    def seqs(self) -> list[int]:
        return [int(e["seq"]) for e in self.sent]


@pytest.fixture(autouse=True)
def short_idle(monkeypatch: pytest.MonkeyPatch) -> None:
    # Si une fin « au silence » existait encore, elle se déclencherait pendant ces tests.
    monkeypatch.setattr(replay, "IDLE_CHECK_S", 0.05, raising=False)


@pytest.fixture
async def db(tmp_path: Path) -> AsyncIterator[Factory]:
    engine = create_engine(f"sqlite+aiosqlite:///{(tmp_path / 'replay.db').as_posix()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield create_session_factory(engine)
    await engine.dispose()


async def new_session(db: Factory, status: str, events: int = 0) -> str:
    """Session au statut donné avec `events` messages déjà écrits (seq 1..events)."""
    async with db() as s:
        row = await SessionRepository(s, USER).add(graph="demo", status=status, input={})
        repo = EventRepository(s, USER)
        for seq in range(1, events + 1):
            await repo.add(session_id=row.id, seq=seq, type="user.message", payload={"text": "x"})
        await s.commit()
    return row.id


async def set_status(db: Factory, sid: str, status: str) -> None:
    async with db() as s:
        await s.execute(update(AgentSession).where(AgentSession.id == sid).values(status=status))
        await s.commit()


def stream(ws: FakeSocket, bus: EventBus, db: Factory, sid: str, after: int = 0) -> Any:
    async def read_status() -> str:
        async with db() as s:
            row = await SessionRepository(s, USER).get(sid)
        assert row is not None
        return row.status

    async def read_last_seq() -> int:
        async with db() as s:
            return await EventRepository(s, USER).max_seq(sid)

    return asyncio.ensure_future(
        replay.stream_to_socket(
            ws,  # type: ignore[arg-type]
            bus,
            USER,
            sid,
            after,
            read_status=read_status,
            read_last_seq=read_last_seq,
        )
    )


async def test_live_subscriber_gets_run_completed_then_1000(db: Factory):
    """Statut `completed` déjà écrit, `run.completed` pas encore publié (ordre du runner) : le
    flux attend l'événement final, quel que soit le silence entre les deux."""
    bus = EventBus(db)
    sid = await new_session(db, "running", events=2)
    await set_status(db, sid, "completed")
    ws = FakeSocket()
    task = stream(ws, bus, db, sid)
    async with asyncio.timeout(5):
        while len(ws.sent) < 2:
            await asyncio.sleep(0.01)
    await asyncio.sleep(0.4)
    assert ws.closed is None
    await bus.publish(user_id=USER, session_id=sid, type="run.completed", payload={"summary": ""})
    await asyncio.wait_for(task, 5)
    assert [e["type"] for e in ws.sent][-1] == "run.completed"
    assert ws.closed == 1000 and ws.sent_before_close == 3


async def test_stalled_sends_never_close_early(db: Factory):
    """Abonné tardif d'une session finie, client qui bloque 0,5 s sur deux envois."""
    bus = EventBus(db)
    sid = await new_session(db, "completed", events=4)
    await bus.publish(user_id=USER, session_id=sid, type="run.completed", payload={"summary": ""})
    await bus.close(user_id=USER, session_id=sid)
    ws = FakeSocket(pauses={1: 0.5, 3: 0.5})
    await asyncio.wait_for(stream(ws, bus, db, sid), 5)
    assert ws.seqs() == [1, 2, 3, 4, 5]
    assert ws.closed == 1000 and ws.sent_before_close == 5


async def test_late_subscriber_of_cancelled_session_receives_everything(db: Factory):
    """Annulée (aucun événement final), longue histoire (plusieurs lots de rejeu), envois lents
    par moments : tout arrive, puis 1000."""
    bus = EventBus(db)
    sid = await new_session(db, "cancelled", events=1200)
    ws = FakeSocket(pauses={10: 0.3, 600: 0.3, 1199: 0.3})
    await asyncio.wait_for(stream(ws, bus, db, sid, after=5), 8)
    assert ws.seqs() == list(range(6, 1201))
    assert ws.closed == 1000 and ws.sent_before_close == 1195


async def test_cancelled_session_without_events_closes_at_once(db: Factory):
    bus = EventBus(db)
    sid = await new_session(db, "cancelled")
    ws = FakeSocket()
    await asyncio.wait_for(stream(ws, bus, db, sid), 5)
    assert ws.sent == [] and ws.closed == 1000


async def test_open_session_stays_open_until_the_client_leaves(db: Factory):
    bus = EventBus(db)
    sid = await new_session(db, "waiting_user", events=3)
    ws = FakeSocket()
    task = stream(ws, bus, db, sid)
    await asyncio.sleep(0.4)
    assert ws.seqs() == [1, 2, 3] and ws.closed is None
    assert bus.subscriber_count(user_id=USER, session_id=sid) == 1
    ws.gone.set()
    await asyncio.wait_for(task, 5)
    assert ws.closed is None
    assert bus.subscriber_count(user_id=USER, session_id=sid) == 0


async def test_bus_close_ends_the_stream(db: Factory):
    """Abonné présent quand la session est annulée : le `close` du bus termine le flux."""
    bus = EventBus(db)
    sid = await new_session(db, "running", events=1)
    ws = FakeSocket()
    task = stream(ws, bus, db, sid)
    async with asyncio.timeout(5):
        while not ws.sent:
            await asyncio.sleep(0.01)
    await set_status(db, sid, "cancelled")
    await bus.close(user_id=USER, session_id=sid)
    await asyncio.wait_for(task, 5)
    assert ws.seqs() == [1] and ws.closed == 1000
