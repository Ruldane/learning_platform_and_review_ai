"""L'étude guidée dans la vie de l'application (D103) : ce que les routes et le port du Tuteur
(`AgentStudyStore`) partagent : base, lanceur de sessions, programme (verrou, tâches cochées),
mémoire (reflet des niveaux), horloge et verrou par utilisatrice. Créé par le lifespan avant le
moteur d'agents (`app.state.study`), avec le lanceur encore non lié."""

import asyncio
import weakref
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import local_today, user_zone
from app.features.lessons.service.runtime import Launcher
from app.features.memory.service.runtime import MemoryRuntime
from app.features.program.service.runtime import ProgramRuntime
from app.features.settings.service import SettingsService

GRAPH = "study_session"
SUBJECT = "study_session"  # sujet de la session d'agents : la session d'étude (D103)


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class StudyRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    launcher: Launcher
    program: ProgramRuntime
    memory: MemoryRuntime
    now: Callable[[], datetime] = utc_now  # remplacée par les tests (heure figée)
    _locks: weakref.WeakValueDictionary[str, asyncio.Lock] = field(
        default_factory=weakref.WeakValueDictionary, repr=False, compare=False
    )

    @asynccontextmanager
    async def study_lock(self, user_id: str) -> AsyncIterator[None]:
        """Départ, fin et abandon d'une session d'une utilisatrice passent l'un après l'autre.
        Pris AVANT le verrou du programme (jamais l'inverse). Propre à ce processus (un seul
        worker) ; l'index unique `uq_study_sessions_open` reste le dernier rempart."""
        lock = self._locks.get(user_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[user_id] = lock
        async with lock:
            yield

    async def zone(self, db: AsyncSession, user_id: str) -> ZoneInfo:
        return user_zone((await SettingsService(db, user_id).get()).timezone)

    async def today(self, db: AsyncSession, user_id: str) -> date:
        """Le jour de January dans son fuseau (D98)."""
        return local_today(await self.zone(db, user_id), self.now())
