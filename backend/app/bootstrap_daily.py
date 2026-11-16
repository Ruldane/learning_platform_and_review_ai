"""Composition du quotidien (phase 8, D160) : relevé du radar, puis, au fil de la phase, brief du
jour et projets. Gardée hors de `app.main` (300 lignes) : une feature de plus = un champ de
`DailyRuntimes` et une ligne dans `daily_runtimes`. Comme `app.bootstrap`, seul `app.main`
l'importe (contrat 5)."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.launcher import SessionLauncher
from app.agents.tools.radar_port import RadarStore
from app.bootstrap_agents import StudyRuntimes
from app.bootstrap_career import CareerRuntimes
from app.features.radar.service.runtime import RadarRuntime
from app.features.radar.service.store import AgentRadarStore
from app.features.research.service.runtime import ResearchRuntime


@dataclass(frozen=True)
class DailyRuntimes:
    """Ce que les routes du quotidien lisent sur `app.state.daily`, ce que les tâches planifiées
    reçoivent (`JobContext.daily`) et les ports qu'elles donnent au moteur (`agent_ports`)."""

    radar: RadarRuntime  # relevés, tâche du lundi, demande du marché (D160)
    radar_store: RadarStore  # port du parcours `market_radar` (D159)
    # brief, projects : tâches 8.6 et 8.10


def daily_runtimes(
    session_factory: async_sessionmaker[AsyncSession],
    launcher: SessionLauncher,
    *,
    research: ResearchRuntime,
    career: CareerRuntimes,
    study: StudyRuntimes,
) -> DailyRuntimes:
    """Radar (base, lanceur lié au moteur ensuite, lecture des pages par la recherche web) et son
    port. `career` et `study` : le brief (8.6) et les projets (8.10) les liront."""
    radar = RadarRuntime(session_factory, launcher, research)
    return DailyRuntimes(radar=radar, radar_store=AgentRadarStore(radar))
