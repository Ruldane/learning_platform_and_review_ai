"""Scheduler of the back end's tasks (D91): APScheduler 3.11 (`AsyncIOScheduler`, latest
stable version; 4.x is still a pre-release), in the server's asyncio loop.

- A single instance of a task at a time (`max_instances=1`); a delay (server asleep,
  run still in progress) is caught up ONCE (`coalesce=True`, no bounded grace time).
- First run at startup if `at_startup`.
- A task exception is logged by its type only (never its message, which
  could quote data) and is never propagated: the next run will take place.
- On exit, stop without waiting for a run to finish: `shutdown(wait=False)` (which, in 3.x,
  only applies on the next turn of the loop), then the runs in progress are cancelled and
  awaited here, before the engine and the database close. The lessons' state is enough to
  resume at the next startup."""

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
            logger.info("Scheduled task %s interrupted by the shutdown", spec.name)
        except Exception as exc:
            logger.warning("Scheduled task %s failed (%s)", spec.name, type(exc).__name__)
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
    logger.info("Scheduler started: %d task(s)", len(jobs))
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        await asyncio.sleep(0)  # APScheduler 3.x's shutdown goes through `call_soon_threadsafe`
        pending = list(running)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
