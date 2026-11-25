"""What a scheduled task declares (`JobSpec`) and what it receives (`JobContext`)."""

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
    """What the daily tasks read from `app.bootstrap_daily.DailyRuntimes` (which the scheduler
    cannot
    import, contract 5): one more task = one property here."""

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
    """Composed by `app.bootstrap.scheduler_context`: the database, the session launcher (linked to
    the
    engine), lesson production, replanning (weekly review, D106), applications (follow-ups, D140)
    and the daily (radar readings, D160; morning brief, D162; mini projects' statements, D166)."""

    session_factory: async_sessionmaker[AsyncSession]
    launcher: SessionLauncher
    production: ProductionContext
    replan: ReplanRuntime
    applications: ApplicationsRuntime
    daily: DailyJobs
    book: BookRuntime | None = None


@dataclass(frozen=True)
class JobSpec:
    """`every`: interval between two runs; `at_startup`: one run at startup."""

    name: str
    every: timedelta
    run: Callable[[JobContext], Awaitable[None]]
    at_startup: bool = True
