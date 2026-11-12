"""Les quiz dans la vie de l'application (D101) : ce que les routes et le port de l'Examinateur
(`AgentQuizStore`) partagent : base, lanceur de sessions, programme (verrou, tâches de suivi),
mémoire (reflet des niveaux), horloge et verrous par quiz. Créé par le lifespan avant le moteur
d'agents (`app.state.quiz`), avec le lanceur encore non lié."""

import asyncio
import weakref
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import local_today, user_zone
from app.features.lessons.service.runtime import Launcher
from app.features.memory.service.runtime import MemoryRuntime
from app.features.program.service.runtime import ProgramRuntime
from app.features.settings.service import SettingsService

GRAPH = "quiz"
SUBJECT = "quiz"


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class QuizRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    launcher: Launcher
    program: ProgramRuntime
    memory: MemoryRuntime
    now: Callable[[], datetime] = utc_now  # remplacée par les tests (heure figée)
    # Faible : un verrou que plus personne ne tient disparaît.
    _locks: weakref.WeakValueDictionary[tuple[str, str], asyncio.Lock] = field(
        default_factory=weakref.WeakValueDictionary, repr=False, compare=False
    )

    @asynccontextmanager
    async def quiz_lock(self, user_id: str, key: str) -> AsyncIterator[None]:
        """Lancement d'un quiz (clé : le module) ou d'une tentative (clé : le quiz) : deux
        envois simultanés passent l'un après l'autre. Propre à ce processus (un seul worker) ;
        l'index unique `uq_quiz_attempts_grading` reste le dernier rempart (F3)."""
        lock = self._locks.get((user_id, key))
        if lock is None:
            lock = asyncio.Lock()
            self._locks[(user_id, key)] = lock
        async with lock:
            yield

    async def today(self, db: AsyncSession, user_id: str) -> date:
        """Le jour de January dans son fuseau (D98)."""
        zone = user_zone((await SettingsService(db, user_id).get()).timezone)
        return local_today(zone, self.now())
