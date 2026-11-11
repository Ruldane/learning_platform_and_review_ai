"""Bus d'événements d'une session : écrit chaque événement dans `session_events`, puis le diffuse.

- `publish` valide la charge par le catalogue (les champs hors catalogue sont écartés : rien
  d'imprévu, une clé par exemple, n'est écrit ni diffusé), puis, sous un verrou propre à la
  session, numérote (`seq` = dernier connu + 1, cache initialisé par `max_seq`), écrit et valide
  la ligne, et la pousse dans la file de chaque abonné : l'ordre des files est celui des `seq`.
  L'unicité `(session_id, seq)` en base reste le filet de sécurité (cache périmé : on relit).
  L'écriture elle-même vit dans `bus_write.py`.
- `publish_with` ajoute une garde exécutée dans la transaction de l'événement : l'issue d'une
  session (statut final) et son événement sont validés ensemble, ou pas du tout (D61).
- `subscribe` inscrit sa file AVANT toute lecture, rejoue la base après `after_seq`, puis passe
  au direct en ignorant tout `seq` déjà émis : ni trou ni doublon.
- File bornée : pleine, elle cesse de recevoir ; son abonné la vide puis repasse par le rejeu.
  De même si le direct saute un numéro (écrivain hors du bus) : rejeu depuis le dernier reçu.
- `flush` attend les écritures protégées en vol, de toutes les sessions ou d'une seule (N5) ;
  `aclose` (arrêt du serveur) les attend toutes.

Un seul bus par processus (`app.state`) : la diffusion en direct est en mémoire.
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus_state import SessionState, Subscriber, to_event
from app.agents.runtime.bus_write import EventWriter, Guard
from app.agents.runtime.events import EventType, SessionEvent, validate_payload
from app.agents.runtime.repositories import EventRepository

__all__ = ["EventBus", "Guard"]

QUEUE_SIZE = 1000
REPLAY_BATCH = 500

type _Key = tuple[str, str]  # (user_id, session_id) : l'isolation par utilisateur vaut aussi ici
type _Publication = asyncio.Task[SessionEvent | None]


class EventBus:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        queue_size: int = QUEUE_SIZE,
        replay_batch: int = REPLAY_BATCH,
    ) -> None:
        self._factory = session_factory
        self._writer = EventWriter(session_factory)
        self._queue_size = queue_size
        self._replay_batch = replay_batch
        self._states: dict[_Key, SessionState] = {}
        self._inflight: dict[_Key, set[_Publication]] = {}

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
        event = await self._protected(user_id, session_id, type, payload, agent, None)
        if event is None:  # impossible : sans garde, rien ne refuse l'écriture
            raise RuntimeError("publication sans garde refusée")
        return event

    async def publish_with(
        self,
        *,
        user_id: str,
        session_id: str,
        type: EventType,
        payload: BaseModel | dict[str, Any],
        guard: Guard,
        agent: str | None = None,
    ) -> SessionEvent | None:
        """Comme `publish`, avec `guard(db)` appelée dans la transaction de l'événement (sous le
        verrou de la session) : `False` → rien n'est écrit ni diffusé, `None` ; `True` → garde
        et événement validés ensemble, puis diffusion. Si l'insertion échoue, la garde est
        annulée avec elle (D52 §2, D61)."""
        return await self._protected(user_id, session_id, type, payload, agent, guard)

    async def _protected(
        self,
        user_id: str,
        session_id: str,
        type: EventType,
        payload: BaseModel | dict[str, Any],
        agent: str | None,
        guard: Guard | None,
    ) -> SessionEvent | None:
        data = validate_payload(type, payload).model_dump(mode="json")
        key = (user_id, session_id)
        task = asyncio.ensure_future(self._publish(key, type, data, agent, guard))
        tasks = self._inflight.setdefault(key, set())
        tasks.add(task)
        task.add_done_callback(lambda done: self._landed(key, done))
        return await asyncio.shield(task)

    def _landed(self, key: _Key, task: _Publication) -> None:
        tasks = self._inflight.get(key)
        if tasks is not None:
            tasks.discard(task)
            if not tasks:
                del self._inflight[key]

    async def _publish(
        self, key: _Key, type: str, data: dict[str, Any], agent: str | None, guard: Guard | None
    ) -> SessionEvent | None:
        user_id, session_id = key
        while True:
            state = self._state(key)
            state.publishers += 1
            try:
                async with state.lock:
                    if state.closed:
                        continue  # `close` a retiré cet état pendant l'attente du verrou
                    row = await self._writer.write(
                        state, user_id, session_id, type, data, agent, guard
                    )
                    if row is None:
                        return None  # garde refusée : rien d'écrit, rien à diffuser
                    event = to_event(row)
                    for sub in state.subscribers:
                        sub.offer(event)
                    return event
            finally:
                state.publishers -= 1
                self._release(key, state)

    # --- Abonnement ----------------------------------------------------------------------

    async def subscribe(
        self, *, user_id: str, session_id: str, after_seq: int = 0
    ) -> AsyncGenerator[SessionEvent, None]:
        """Rejeu des événements `seq > after_seq` puis direct, sans trou ni doublon.

        Se termine après `close` de la session ; à fermer par `aclose` (ou `aclosing`).
        """
        key = (user_id, session_id)
        state = self._state(key)
        sub = Subscriber(asyncio.Queue(self._queue_size))
        state.subscribers.add(sub)  # 1. inscrire la file avant toute lecture en base
        last = after_seq
        try:
            while True:
                # Avant la relecture : la file reçoit de nouveau, rien ne tombe entre les deux.
                sub.overflowed = False
                while True:  # 2. rejeu par lots
                    batch = await self._read_after(user_id, session_id, last)
                    for event in batch:
                        yield event
                        last = event.seq
                    if len(batch) < self._replay_batch:
                        break
                gap = False
                while (live := await sub.next_live()) is not None:  # 3. direct
                    if live.seq <= last:
                        continue  # déjà émis (rejeu)
                    if live.seq > last + 1:
                        gap = True  # écrivain hors du bus : la base a ce qui manque
                        break
                    yield live
                    last = live.seq
                if not (gap or sub.overflowed):
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
        return [to_event(row) for row in rows]

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

    async def flush(self, *, user_id: str | None = None, session_id: str | None = None) -> None:
        """Attend les publications déjà commencées (protégées : leur appelant a pu être annulé,
        elles continuent sans lui) : toutes, ou seulement celles de la session `(user_id,
        session_id)` (N5). Après l'arrêt d'une tâche (pause, annulation), tout ce qu'elle
        publiait est écrit : le `last_seq` lu ensuite le compte (D56)."""
        if (user_id is None) != (session_id is None):
            raise ValueError("flush : user_id et session_id vont ensemble")
        if user_id is None or session_id is None:
            pending = [task for tasks in self._inflight.values() for task in tasks]
        else:
            pending = list(self._inflight.get((user_id, session_id), ()))
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    async def aclose(self) -> None:
        """Arrêt du serveur, avant la fermeture du moteur : attend les écritures protégées
        encore en vol, jusqu'à ce qu'il n'en reste aucune."""
        while self._inflight:
            await self.flush()

    def subscriber_count(self, *, user_id: str, session_id: str) -> int:
        state = self._states.get((user_id, session_id))
        return len(state.subscribers) if state is not None else 0

    def queued(self, *, user_id: str, session_id: str) -> int:
        """Événements en attente dans les files des abonnés (borné par `queue_size`)."""
        state = self._states.get((user_id, session_id))
        return sum(s.queue.qsize() for s in state.subscribers) if state is not None else 0

    def tracked_sessions(self) -> int:
        return len(self._states)

    def _state(self, key: _Key) -> SessionState:
        state = self._states.get(key)
        if state is None:
            state = self._states[key] = SessionState()
        return state

    def _release(self, key: _Key, state: SessionState) -> None:
        """Oublie un état devenu inutile : ni abonné, ni publication, ni `seq` en cache (une
        session jamais publiée ici, ou d'un autre utilisateur). Le cache, lui, vit jusqu'à
        `close`, pour ne pas relire `max_seq` à chaque événement d'une session sans abonné."""
        if state.subscribers or state.publishers or state.last_seq is not None:
            return
        state.closed = True
        if self._states.get(key) is state:
            del self._states[key]
