"""Planificateur (D91) : passage au démarrage, une instance à la fois, exception journalisée par
son type et jamais propagée, passage en cours annulé à l'arrêt."""

import asyncio
import logging
from datetime import timedelta

import pytest

from app.scheduler.base import JobContext, JobSpec
from app.scheduler.registry import JOBS
from app.scheduler.runner import open_scheduler

CTX = JobContext(None, None, None)  # type: ignore[arg-type]  # les tâches de test ne le lisent pas


async def wait_for(predicate: object, timeout: float = 3.0) -> None:
    async with asyncio.timeout(timeout):
        while not predicate():  # type: ignore[operator]
            await asyncio.sleep(0.01)


def test_lessons_due_runs_every_six_hours_and_at_startup() -> None:
    assert [(j.name, j.every, j.at_startup) for j in JOBS] == [
        ("lessons_due", timedelta(hours=6), True)
    ]


async def test_scheduler_runs_jobs_at_startup_and_survives_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    runs: list[str] = []

    async def broken(ctx: JobContext) -> None:
        runs.append("broken")
        raise RuntimeError("donnée secrète de January")

    async def counted(ctx: JobContext) -> None:
        runs.append("counted")

    async def later(ctx: JobContext) -> None:
        runs.append("later")

    jobs = [
        JobSpec("broken", timedelta(seconds=0.05), broken),
        JobSpec("counted", timedelta(hours=6), counted),
        JobSpec("later", timedelta(hours=6), later, at_startup=False),
    ]
    async with open_scheduler(jobs, CTX):
        await wait_for(lambda: runs.count("broken") >= 3 and "counted" in runs)
    assert "later" not in runs and runs.count("counted") == 1
    assert "RuntimeError" in caplog.text
    assert "secrète" not in caplog.text


async def test_one_instance_at_a_time_and_stop_cancels_the_running_pass() -> None:
    started, cancelled = [], []
    gate = asyncio.Event()

    async def slow(ctx: JobContext) -> None:
        started.append(1)
        try:
            await gate.wait()
        except asyncio.CancelledError:
            cancelled.append(1)
            raise

    async with open_scheduler([JobSpec("slow", timedelta(seconds=0.02), slow)], CTX):
        await wait_for(lambda: started)
        await asyncio.sleep(0.2)  # dix échéances passent : aucune seconde instance
        assert len(started) == 1
    assert cancelled == [1]
