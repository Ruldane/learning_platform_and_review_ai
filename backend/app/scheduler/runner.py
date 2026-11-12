"""Planificateur des tâches du back (D91) : APScheduler 3.11 (`AsyncIOScheduler`, dernière
version stable ; la 4.x est encore en préversion), dans la boucle asyncio du serveur.

- Une seule instance d'une tâche à la fois (`max_instances=1`) ; un retard (serveur endormi,
  passage encore en cours) est rattrapé UNE fois (`coalesce=True`, sans délai de grâce borné).
- Premier passage dès le démarrage si `at_startup`.
- Une exception de tâche est journalisée par son type seulement (jamais son message, qui
  pourrait citer une donnée) et n'est jamais propagée : le passage suivant aura lieu.
- À la sortie, arrêt sans attendre la fin d'un passage : `shutdown(wait=False)` (qui, en 3.x,
  ne s'applique qu'au tour suivant de la boucle), puis les passages en cours sont annulés et
  attendus ici, avant la fermeture du moteur et de la base. L'état des leçons suffit à
  reprendre au prochain démarrage."""

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.scheduler.base import JobContext, JobSpec

logger = logging.getLogger(__name__)


def guarded(
    spec: JobSpec, context: JobContext, running: set[asyncio.Task[object]]
) -> Callable[[], Awaitable[None]]:
    async def run() -> None:
        task = asyncio.current_task()
        if task is not None:
            running.add(task)
        try:
            await spec.run(context)
        except asyncio.CancelledError:
            logger.info("Tâche planifiée %s interrompue par l'arrêt", spec.name)
        except Exception as exc:
            logger.warning("Tâche planifiée %s en échec (%s)", spec.name, type(exc).__name__)
        finally:
            if task is not None:
                running.discard(task)

    return run


@asynccontextmanager
async def open_scheduler(jobs: Sequence[JobSpec], context: JobContext) -> AsyncIterator[None]:
    scheduler = AsyncIOScheduler(timezone=UTC)
    running: set[asyncio.Task[object]] = set()
    for spec in jobs:
        first = {"next_run_time": datetime.now(UTC)} if spec.at_startup else {}
        scheduler.add_job(
            guarded(spec, context, running),
            "interval",
            seconds=spec.every.total_seconds(),
            id=spec.name,
            name=spec.name,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=None,
            **first,
        )
    scheduler.start()
    logger.info("Planificateur démarré : %d tâche(s)", len(jobs))
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        await asyncio.sleep(0)  # l'arrêt d'APScheduler 3.x passe par `call_soon_threadsafe`
        pending = list(running)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
