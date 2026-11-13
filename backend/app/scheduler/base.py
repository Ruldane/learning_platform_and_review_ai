"""Ce qu'une tâche planifiée déclare (`JobSpec`) et ce qu'elle reçoit (`JobContext`)."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.launcher import SessionLauncher
from app.features.lessons.service.production import ProductionContext
from app.features.replan.service.runtime import ReplanRuntime


@dataclass(frozen=True)
class JobContext:
    """Composé par `app.bootstrap.scheduler_context` : la base, le lanceur de sessions (lié au
    moteur), la production des leçons et la replanification (bilan hebdomadaire, D106)."""

    session_factory: async_sessionmaker[AsyncSession]
    launcher: SessionLauncher
    production: ProductionContext
    replan: ReplanRuntime


@dataclass(frozen=True)
class JobSpec:
    """`every` : intervalle entre deux passages ; `at_startup` : un passage dès le démarrage."""

    name: str
    every: timedelta
    run: Callable[[JobContext], Awaitable[None]]
    at_startup: bool = True
