"""Tâche « relances » (SPEC 6.2, D140) : toutes les heures et au démarrage, adopte les versions de
CV de chaque utilisatrice puis synchronise ses relances ; une panne chez l'une n'arrête pas
l'autre. La tâche ne fait que déballer son contexte (contrat 8)."""

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.db.models.accounts import User
from app.db.models.applications import Application, Reminder
from app.features.applications.service import reminders
from app.features.applications.service.runtime import ApplicationsRuntime
from app.scheduler.base import JobContext
from app.scheduler.jobs import reminders_due
from app.scheduler.registry import JOBS
from tests.features.lessons.conftest import ME, OTHER
from tests.features.program.support import Factory

NOW = datetime(2026, 11, 15, 10, 0, tzinfo=UTC)
ALL = ["linkedin_7", "email_14", "close_21"]


async def _seed(factory: Factory) -> None:
    async with factory() as db:
        for user_id in (ME, OTHER):
            db.add(User(id=user_id, user_id=user_id, name=user_id))
        for user_id, company, days in ((ME, "Société Fictive", 7), (OTHER, "Autre SA", 14)):
            db.add(
                Application(
                    user_id=user_id,
                    company=company,
                    company_norm=company.lower(),
                    title="Poste",
                    status="applied",
                    applied_on=date(2026, 11, 15) - timedelta(days=days),
                )  # fmt: skip
            )
        await db.commit()


def _context(job_ctx: JobContext) -> JobContext:
    rt = ApplicationsRuntime(job_ctx.session_factory, job_ctx.launcher, now=lambda: NOW)
    return JobContext(
        job_ctx.session_factory, job_ctx.launcher, job_ctx.production, job_ctx.replan, rt
    )


async def _reminders(factory: Factory) -> dict[str, list[str]]:
    async with factory() as db:
        rows = (await db.execute(select(Reminder).order_by(Reminder.due_on))).scalars().all()
        return {user: [r.kind for r in rows if r.user_id == user] for user in (ME, OTHER)}


def test_job_is_registered_hourly_at_startup() -> None:
    [spec] = [j for j in JOBS if j.name == "reminders_due"]
    assert spec.every == timedelta(hours=1) and spec.at_startup


async def test_job_runs_for_each_user(job_ctx: JobContext) -> None:
    await _seed(job_ctx.session_factory)
    ctx = _context(job_ctx)
    await reminders_due.run(ctx)
    assert await _reminders(ctx.session_factory) == {ME: ALL, OTHER: ALL}
    await reminders_due.run(ctx)  # idempotente
    async with ctx.session_factory() as db:
        assert len((await db.execute(select(Reminder))).scalars().all()) == 6


async def test_one_failing_user_does_not_stop_the_others(
    job_ctx: JobContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _seed(job_ctx.session_factory)
    real = reminders.sync_user

    async def flaky(db: object, user_id: str, today: date, **kw: object) -> None:
        if user_id == ME:
            raise RuntimeError("panne")
        await real(db, user_id, today, **kw)  # type: ignore[arg-type]

    monkeypatch.setattr(reminders, "sync_user", flaky)
    await reminders_due.run(_context(job_ctx))
    assert await _reminders(job_ctx.session_factory) == {ME: [], OTHER: ALL}
