"""Écriture d'un événement par le bus, verrou de la session tenu par l'appelant (`bus.py`).

- Numérotation : `seq` = dernier connu + 1 (cache `SessionState.last_seq`, initialisé par
  `max_seq`). L'unicité `(session_id, seq)` en base reste le filet de sécurité : un `seq` refusé
  (écrivain hors du bus) fait relire `max_seq` et rejouer la transaction ENTIÈRE.
- Garde facultative (`publish_with`, D61) : appelée dans la transaction de l'événement, avant
  l'insertion. `False` : rollback, rien n'est écrit. `True` : l'événement est inséré dans la
  même transaction, puis tout est validé d'un seul commit ; si l'insertion ou le commit
  échoue, ce que la garde a écrit est annulé avec lui (jamais de statut final sans son
  événement, D52 §2). La garde doit commencer par son écriture (pas de lecture avant) : SQLite
  applique alors le délai d'attente sur verrou au lieu d'échouer.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus_state import SessionState
from app.agents.runtime.repositories import EventRepository, SessionRepository
from app.core.errors import AppError
from app.db.models.agents import SessionEventRecord

type Guard = Callable[[AsyncSession], Awaitable[bool]]

_WRITE_ATTEMPTS = 3


class EventWriter:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def write(
        self,
        state: SessionState,
        user_id: str,
        session_id: str,
        type: str,
        data: dict[str, Any],
        agent: str | None,
        guard: Guard | None = None,
    ) -> SessionEventRecord | None:
        """Numérote et écrit ; `None` si la garde refuse (rien d'écrit, cache intact). Toute
        erreur autre qu'un `seq` refusé invalide le cache : la base tranchera au prochain."""
        attempt = 0
        while True:
            attempt += 1
            if state.last_seq is None:
                state.last_seq = await self.load_last_seq(user_id, session_id)
            seq = state.last_seq + 1
            try:
                row = await self.insert(user_id, session_id, seq, type, data, agent, guard)
            except IntegrityError:
                state.last_seq = None
                if attempt >= _WRITE_ATTEMPTS:
                    raise
                continue
            except BaseException:
                state.last_seq = None  # issue inconnue (validée ou non)
                raise
            if row is not None:
                state.last_seq = seq
            return row

    async def load_last_seq(self, user_id: str, session_id: str) -> int:
        # Lecture dans sa propre transaction : l'écriture qui suit commence par une écriture
        # (garde ou INSERT), si bien que SQLite applique le délai d'attente au lieu d'échouer.
        async with self._factory() as db:
            if await SessionRepository(db, user_id).get(session_id) is None:
                raise AppError("session_not_found", "Session introuvable.", status_code=404)
            return await EventRepository(db, user_id).max_seq(session_id)

    async def insert(
        self,
        user_id: str,
        session_id: str,
        seq: int,
        type: str,
        data: dict[str, Any],
        agent: str | None,
        guard: Guard | None = None,
    ) -> SessionEventRecord | None:
        async with self._factory() as db:
            if guard is not None and not await guard(db):
                await db.rollback()
                return None
            row = await EventRepository(db, user_id).add(
                session_id=session_id, seq=seq, type=type, agent=agent, payload=data
            )
            await db.commit()
        return row
