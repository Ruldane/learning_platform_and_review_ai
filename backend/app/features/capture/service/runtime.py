"""La capture rapide dans la vie de l'application (D108) : ce que la route `POST /capture` et le
port de l'Archiviste (`AgentCaptureStore`) partagent : base, lanceur de sessions (lié au moteur
ensuite), programme (verrou, tâches cochées), mémoire (élément rangé, reflet des acquis) et
horloge. Créé par le lifespan avant le moteur d'agents (`app.state.capture`)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import local_today, user_zone
from app.features.lessons.service.runtime import Launcher
from app.features.memory.service.runtime import MemoryRuntime
from app.features.program.service.runtime import ProgramRuntime
from app.features.settings.service import SettingsService

GRAPH = "capture"


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class CaptureRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    launcher: Launcher
    program: ProgramRuntime
    memory: MemoryRuntime
    now: Callable[[], datetime] = utc_now  # remplacée par les tests (heure figée)

    async def today(self, db: AsyncSession, user_id: str) -> date:
        """Le jour de January dans son fuseau (D98)."""
        zone = user_zone((await SettingsService(db, user_id).get()).timezone)
        return local_today(zone, self.now())
