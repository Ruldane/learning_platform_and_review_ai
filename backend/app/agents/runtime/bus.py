"""Bus d'événements d'une session : écrit chaque événement dans `session_events`, puis le diffuse.

- `publish` valide la charge par le catalogue (les champs hors catalogue sont écartés : rien
  d'imprévu, une clé par exemple, n'est écrit ni diffusé), puis, sous un verrou propre à la
  session, numérote (`seq` = dernier connu + 1, cache initialisé par `max_seq`), écrit et valide
  la ligne, et la pousse dans la file de chaque abonné : l'ordre des files est celui des `seq`.
  L'unicité `(session_id, seq)` en base reste le filet de sécurité (cache périmé : on relit).
- `subscribe` inscrit sa file AVANT toute lecture, rejoue la base après `after_seq`, puis passe
  au direct en ignorant tout `seq` déjà émis : ni trou ni doublon.
- File bornée : pleine, elle cesse de recevoir ; son abonné la vide puis repasse par le rejeu.

Un seul bus par processus (`app.state`) : la diffusion en direct est en mémoire.
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.events import (
    SESSION_EVENT_ADAPTER,
    EventType,
    SessionEvent,
    validate_payload,
)
from app.agents.runtime.repositories import EventRepository, SessionRepository
from app.core.errors import AppError
from app.db.models.agents import SessionEventRecord

QUEUE_SIZE = 1000
REPLAY_BATCH = 500
_WRITE_ATTEMPTS = 3

type _Key = tuple[str, str]  # (user_id, session_id) : l'isolation par utilisateur vaut aussi ici


@dataclass(eq=False)
class _Subscriber:
    """File d'un abonné ; `None` en file signale la fin de la session."""

    queue: asyncio.Queue[SessionEvent | None]
    overflowed: bool = False  # file pleine : plus rien n'y entre jusqu'au prochain rejeu
    closed: bool = False

    def offer(self, event: SessionEvent) -> None:
        if self.overflowed:
            return
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            self.overflowed = True

    def close(self) -> None:
        self.closed = True
        with suppress(asyncio.QueueFull):  # file pleine : `closed` suffit, vue une fois vidée
            self.queue.put_nowait(None)

    async def next_live(self) -> SessionEvent | None:
        """Prochain événement en file ; `None` quand il faut rejouer (débordement) ou finir."""
        if self.queue.empty() and (self.overflowed or self.closed):
            return None
        return await self.queue.get()


@dataclass(eq=False)
class _SessionState:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_seq: int | None = None  # None : à relire en base
    subscribers: set[_Subscriber] = field(default_factory=set)
    publishers: int = 0  # publications en cours ou en attente du verrou
    closed: bool = False  # retiré du bus : un publieur en attente reprend avec le nouvel état


def _to_event(row: SessionEventRecord) -> SessionEvent:
    return SESSION_EVENT_ADAPTER.validate_python(
        {
            "id": row.id,
            "session_id": row.session_id,
            "seq": row.seq,
            "ts": row.created_at,
            "type": row.type,
            "agent": row.agent,
            "payload": row.payload,
        }
    )


class EventBus:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        queue_size: int = QUEUE_SIZE,
        replay_batch: int = REPLAY_BATCH,
    ) -> None:
        self._factory = session_factory
        self._queue_size = queue_size
        self._replay_batch = replay_batch
        self._states: dict[_Key, _SessionState] = {}
        self._inflight: set[asyncio.Task[SessionEvent]] = set()

    # --- Publication ---------------------------------------------------------------------

    async def publish(
        self,
        *,
        user_id: str,
        session_id: str,
        type: EventType,
        payload: BaseModel | dict[str, Any],
        agent: str | None = None,
    ) -> SessionEvent:
        """Écrit puis diffuse ; `ValueError` si la charge ne suit pas le catalogue,
        `AppError("session_not_found")` si la session n'appartient pas à `user_id`.

        L'écriture et la diffusion forment une tâche protégée : annuler l'appelant (session
        annulée en pleine publication) ne laisse jamais un événement écrit mais non diffusé.
        """
        data = validate_payload(type, payload).model_dump(mode="json")
        task = asyncio.ensure_future(self._publish(user_id, session_id, type, data, agent))
        self._inflight.add(task)
        task.add_done_callback(self._inflight.discard)
        return await asyncio.shield(task)

    async def _publish(
        self, user_id: str, session_id: str, type: str, data: dict[str, Any], agent: str | None
    ) -> SessionEvent:
        key = (user_id, session_id)
        while True:
            state = self._state(key)
            state.publishers += 1
            try:
                async with state.lock:
                    if state.closed:
                        continue  # `close` a retiré cet état pendant l'attente du verrou
                    event = await self._write(state, user_id, session_id, type, data, agent)
                    for sub in state.subscribers:
                        sub.offer(event)
                    return event
            finally:
                state.publishers -= 1
                self._release(key, state)

    async def _write(
        self,
        state: _SessionState,
        user_id: str,
        session_id: str,
        type: str,
        data: dict[str, Any],
        agent: str | None,
    ) -> SessionEvent:
        """Numérote et écrit (verrou de session tenu) ; relit `max_seq` si la base refuse le
        `seq` (écrivain hors de ce bus) ; toute autre erreur invalide le cache."""
        attempt = 0
        while True:
            attempt += 1
            if state.last_seq is None:
                state.last_seq = await self._load_last_seq(user_id, session_id)
            seq = state.last_seq + 1
            try:
                row = await self._insert(user_id, session_id, seq, type, data, agent)
            except IntegrityError:
                state.last_seq = None
                if attempt >= _WRITE_ATTEMPTS:
                    raise
                continue
            except BaseException:
                state.last_seq = None  # issue inconnue (validée ou non) : la base tranchera
                raise
            state.last_seq = seq
            return _to_event(row)

    async def _load_last_seq(self, user_id: str, session_id: str) -> int:
        # Lecture dans sa propre transaction : l'écriture qui suit commence par l'INSERT, si
        # bien que SQLite applique le délai d'attente (busy timeout) au lieu d'échouer.
        async with self._factory() as db:
            if await SessionRepository(db, user_id).get(session_id) is None:
                raise AppError("session_not_found", "Session introuvable.", status_code=404)
            return await EventRepository(db, user_id).max_seq(session_id)

    async def _insert(
        self,
        user_id: str,
        session_id: str,
        seq: int,
        type: str,
        data: dict[str, Any],
        agent: str | None,
    ) -> SessionEventRecord:
        async with self._factory() as db:
            row = await EventRepository(db, user_id).add(
                session_id=session_id, seq=seq, type=type, agent=agent, payload=data
            )
            await db.commit()
        return row

    async def last_seq(self, *, user_id: str, session_id: str) -> int:
        state = self._states.get((user_id, session_id))
        if state is not None and state.last_seq is not None:
            return state.last_seq
        async with self._factory() as db:
            return await EventRepository(db, user_id).max_seq(session_id)

    # --- Abonnement ----------------------------------------------------------------------

    async def subscribe(
        self, *, user_id: str, session_id: str, after_seq: int = 0
    ) -> AsyncGenerator[SessionEvent, None]:
        """Rejeu des événements `seq > after_seq` puis direct, sans trou ni doublon.

        Se termine après `close` de la session ; à fermer par `aclose` (ou `aclosing`).
        """
        key = (user_id, session_id)
        state = self._state(key)
        sub = _Subscriber(asyncio.Queue(self._queue_size))
        state.subscribers.add(sub)  # 1. inscrire la file avant toute lecture en base
        last = after_seq
        try:
            while True:
                sub.overflowed = False  # file vide : elle reçoit de nouveau, avant la relecture
                while True:  # 2. rejeu par lots
                    batch = await self._read_after(user_id, session_id, last)
                    for event in batch:
                        yield event
                        last = event.seq
                    if len(batch) < self._replay_batch:
                        break
                while (live := await sub.next_live()) is not None:  # 3. direct
                    if live.seq > last:
                        yield live
                        last = live.seq
                if not sub.overflowed:
                    return  # session fermée
        finally:  # 4. désinscrire
            state.subscribers.discard(sub)
            self._release(key, state)

    async def _read_after(
        self, user_id: str, session_id: str, after_seq: int
    ) -> list[SessionEvent]:
        async with self._factory() as db:
            rows = await EventRepository(db, user_id).list_after(
                session_id, after_seq, limit=self._replay_batch
            )
        return [_to_event(row) for row in rows]

    # --- Fin de session et état mémoire --------------------------------------------------

    async def close(self, *, user_id: str, session_id: str) -> None:
        """Fin de session (statut terminal) : les abonnés reçoivent ce qui est en file puis
        s'arrêtent ; l'état mémoire (verrou, cache, abonnés) est libéré. Un `publish` ultérieur
        repart de la base."""
        key = (user_id, session_id)
        state = self._states.get(key)
        if state is None:
            return
        async with state.lock:  # attend la publication en cours
            state.closed = True
            if self._states.get(key) is state:
                del self._states[key]
            for sub in state.subscribers:
                sub.close()

    def subscriber_count(self, *, user_id: str, session_id: str) -> int:
        state = self._states.get((user_id, session_id))
        return len(state.subscribers) if state is not None else 0

    def queued(self, *, user_id: str, session_id: str) -> int:
        """Événements en attente dans les files des abonnés (borné par `queue_size`)."""
        state = self._states.get((user_id, session_id))
        return sum(s.queue.qsize() for s in state.subscribers) if state is not None else 0

    def tracked_sessions(self) -> int:
        return len(self._states)

    def _state(self, key: _Key) -> _SessionState:
        state = self._states.get(key)
        if state is None:
            state = self._states[key] = _SessionState()
        return state

    def _release(self, key: _Key, state: _SessionState) -> None:
        """Oublie un état devenu inutile : ni abonné, ni publication, ni `seq` en cache (une
        session jamais publiée ici, ou d'un autre utilisateur). Le cache, lui, vit jusqu'à
        `close`, pour ne pas relire `max_seq` à chaque événement d'une session sans abonné."""
        if state.subscribers or state.publishers or state.last_seq is not None:
            return
        state.closed = True
        if self._states.get(key) is state:
            del self._states[key]
