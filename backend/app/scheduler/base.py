"""Ce qu'une tâche planifiée déclare (`JobSpec`) et ce qu'elle reçoit (`JobContext`)."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.launcher import SessionLauncher
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.book.service.runtime import BookRuntime
from app.features.brief.service.runtime import BriefRuntime
from app.features.lessons.service.production import ProductionContext
from app.features.podcast.service.runtime import PodcastRuntime
from app.features.projects.service.runtime import ProjectsRuntime
from app.features.radar.service.runtime import RadarRuntime
from app.features.replan.service.runtime import ReplanRuntime


class DailyJobs(Protocol):
    """Ce que les tâches du quotidien lisent de `app.bootstrap_daily.DailyRuntimes` (que le
    planificateur ne peut pas importer, contrat 5) : une tâche de plus = une propriété ici."""

    @property
    def radar(self) -> RadarRuntime: ...

    @property
    def brief(self) -> BriefRuntime: ...

    @property
    def projects(self) -> ProjectsRuntime: ...

    @property
    def podcast(self) -> PodcastRuntime: ...


@dataclass(frozen=True)
class JobContext:
    """Composé par `app.bootstrap.scheduler_context` : la base, le lanceur de sessions (lié au
    moteur), la production des leçons, la replanification (bilan hebdomadaire, D106) et les
    candidatures (relances, D140) et le quotidien (relevé du radar, D160 ; brief du matin, D162 ;
    énoncés des projets, D166)."""

    session_factory: async_sessionmaker[AsyncSession]
    launcher: SessionLauncher
    production: ProductionContext
    replan: ReplanRuntime
    applications: ApplicationsRuntime
    daily: DailyJobs
    book: BookRuntime | None = None


@dataclass(frozen=True)
class JobSpec:
    """`every` : intervalle entre deux passages ; `at_startup` : un passage dès le démarrage."""

    name: str
    every: timedelta
    run: Callable[[JobContext], Awaitable[None]]
    at_startup: bool = True
