"""Le radar dans la vie de l'application (D160) : ce que les routes, la tâche du lundi et le port
du parcours `market_radar` (`AgentRadarStore`) partagent : base, lanceur de sessions (lié au
moteur ensuite), recherche web (lecture des pages), horloge et verrous. Créé par
`app.bootstrap_daily` avant le moteur d'agents (`app.state.daily.radar`)."""

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
        """Le verrou des relevés d'une utilisatrice : lancement, vérification « déjà en cours ? »
        et correction d'un relevé dont la session est morte forment une seule section."""
        return self.locks.get(user_id, _RUNS)

    def run_lock(self, user_id: str, run_id: str) -> asyncio.Lock:
        """Le verrou d'un relevé : toutes les écritures de son état (lectures simultanées,
        extractions, fin) relisent et réécrivent ses colonnes JSON l'une après l'autre."""
        return self.locks.get(user_id, f"{_RUNS}:{run_id}")
