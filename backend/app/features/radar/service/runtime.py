"""The radar in the application's life (D160): what the routes, the Monday task and the port of
the `market_radar` path (`AgentRadarStore`) share: database, session launcher (bound to the
engine later), web search (reading pages), clock and locks. Created by `app.bootstrap_daily`
before the agent engine (`app.state.daily.radar`)."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.features.lessons.service.runtime import Launcher
from app.features.postings.service.runtime import KeyLocks
from app.features.research.service.runtime import ResearchRuntime

GRAPH = "market_radar"
SUBJECT = "radar_run"
_RUNS = "radar-runs"


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class RadarRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    launcher: Launcher
    research: ResearchRuntime
    now: Callable[[], datetime] = utc_now
    locks: KeyLocks = field(default_factory=KeyLocks, repr=False, compare=False)

    def runs_lock(self, user_id: str) -> asyncio.Lock:
        """The lock on a user's scans: the launch, the check "already running?" and the correction
        of a scan whose session died form a single section."""
        return self.locks.get(user_id, _RUNS)

    def run_lock(self, user_id: str, run_id: str) -> asyncio.Lock:
        """The lock on a scan: all writes to its state (simultaneous reads, extractions, end)
        re-read and rewrite its JSON columns one after the other."""
        return self.locks.get(user_id, f"{_RUNS}:{run_id}")
