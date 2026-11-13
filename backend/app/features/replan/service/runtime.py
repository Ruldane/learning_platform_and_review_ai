"""La replanification dans la vie de l'application (D106) : ce que les routes, le port du
Stratège (`AgentReplanStore`) et le bilan planifié partagent : base, lanceur de sessions (lié au
moteur ensuite), programme (verrou, écriture des versions), horloge et verrous de lancement.
Créé par le lifespan avant le moteur d'agents (`app.state.replan`)."""

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
from app.features.program.service.runtime import ProgramRuntime
from app.features.settings.service import SettingsService

GRAPH = "replan"
SUBJECT = "program"


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class ReplanRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    launcher: Launcher
    program: ProgramRuntime
    now: Callable[[], datetime] = utc_now  # remplacée par les tests (heure figée)
    # Faible : un verrou que plus personne ne tient disparaît.
    _locks: weakref.WeakValueDictionary[tuple[str, str], asyncio.Lock] = field(
        default_factory=weakref.WeakValueDictionary, repr=False, compare=False
    )

    @asynccontextmanager
    async def launch_lock(self, user_id: str, program_id: str) -> AsyncIterator[None]:
        """Lancement d'une replanification : deux demandes simultanées sur un programme passent
        l'une après l'autre (la seconde voit la session de la première : 409 `replan_open`).
        Propre à ce processus (un seul worker)."""
        lock = self._locks.get((user_id, program_id))
        if lock is None:
            lock = asyncio.Lock()
            self._locks[(user_id, program_id)] = lock
        async with lock:
            yield

    async def zone(self, db: AsyncSession, user_id: str) -> ZoneInfo:
        return user_zone((await SettingsService(db, user_id).get()).timezone)

    async def today(self, db: AsyncSession, user_id: str) -> date:
        """Le jour de January dans son fuseau (D98)."""
        return local_today(await self.zone(db, user_id), self.now())
