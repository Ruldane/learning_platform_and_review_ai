"""Quick capture in the life of the application (D108): what the `POST /capture` route and the
Archivist's port (`AgentCaptureStore`) share: database, session launcher (linked to the engine
later), program (lock, checked tasks), memory (stored item, reflection of acquired skills) and
clock. Created by the lifespan before the agent engine (`app.state.capture`)."""

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
    now: Callable[[], datetime] = utc_now  # replaced by the tests (frozen clock)

    async def today(self, db: AsyncSession, user_id: str) -> date:
        """January's day in their time zone (D98)."""
        zone = user_zone((await SettingsService(db, user_id).get()).timezone)
        return local_today(zone, self.now())
