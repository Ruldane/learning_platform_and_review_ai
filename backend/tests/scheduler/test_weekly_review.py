"""Tâche « bilan hebdomadaire » (D106, Review Focus n° 4) : le bilan tombe à l'heure locale de
January (dimanche 18:00 à Paris = 17:00 UTC en novembre), s'écrit une fois par semaine et lance
une seule replanification ; deux semaines de plus de 30 % de retard offrent les options."""

import logging
from datetime import UTC, date, datetime
from typing import Any

import pytest
from sqlalchemy import select

from app.agents.tools.plan_schema import PlanDraft
from app.db.models.study import JournalEntry
from app.features.program.service.runtime import ProgramRuntime
from app.features.replan.service import weekly
from app.features.replan.service.store import AgentReplanStore
from app.features.settings.service import SettingsService
from app.scheduler.base import JobContext
from app.scheduler.jobs import weekly_review
from tests.features.lessons.conftest import ME, OTHER, RecordingLauncher
from tests.features.program.support import Factory, sample_plan
from tests.features.replan.conftest import validated

BEFORE = datetime(2026, 11, 15, 16, 59, tzinfo=UTC)  # dimanche 17:59 à Paris
AFTER = datetime(2026, 11, 15, 17, 1, tzinfo=UTC)  # dimanche 18:01 à Paris
START = date(2026, 11, 9)  # semaines du 9 et du 16/11 : la semaine relue est celle du 9


def _clock(monkeypatch: pytest.MonkeyPatch, now: datetime) -> None:
    """L'heure lue par la tâche (`datetime.now(UTC)`), figée."""

    class Frozen(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> "Frozen":
            return cls.fromtimestamp(now.timestamp(), tz)

    monkeypatch.setattr(weekly_review, "datetime", Frozen)


def _replans(launcher: RecordingLauncher) -> list[dict[str, Any]]:
    """Les lancements `replan` (la validation lance aussi la production des leçons)."""
    return [payload for graph, payload in launcher.started if graph == "replan"]


async def _reviews(factory: Factory) -> list[JournalEntry]:
    async with factory() as db:
        stmt = select(JournalEntry).where(JournalEntry.kind == "weekly_review")
        return list((await db.execute(stmt)).scalars())


async def _zone(factory: Factory, user_id: str, zone: str) -> None:
    async with factory() as db:
        settings = SettingsService(db, user_id)
        await settings.replace((await settings.get()).model_copy(update={"timezone": zone}))
        await db.commit()


async def test_weekly_review_due_at_local_time(
    program_rt: ProgramRuntime,
    job_ctx: JobContext,
    launcher: RecordingLauncher,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paris = await validated(program_rt, ME, start=START)
    new_york = await validated(program_rt, OTHER, start=START)
    await _zone(job_ctx.session_factory, OTHER, "America/New_York")  # 18:00 = 23:00 UTC
    _clock(monkeypatch, BEFORE)
    await weekly_review.run(job_ctx)
    assert await _reviews(job_ctx.session_factory) == [] and _replans(launcher) == []
    _clock(monkeypatch, AFTER)
    await weekly_review.run(job_ctx)
    rows = await _reviews(job_ctx.session_factory)
    assert [(r.user_id, r.ref_key, r.occurred_on) for r in rows] == [
        (ME, f"review:{paris}:2026-11-09", date(2026, 11, 15))
    ]
    assert [p["program_id"] for p in _replans(launcher)] == [paris]
    _clock(monkeypatch, datetime(2026, 11, 15, 23, 1, tzinfo=UTC))  # 18:01 à New York
    await weekly_review.run(job_ctx)
    assert {r.data["program_id"] for r in await _reviews(job_ctx.session_factory)} == {
        paris,
        new_york,
    }


async def test_weekly_review_writes_entry_and_launches_once(
    program_rt: ProgramRuntime,
    job_ctx: JobContext,
    launcher: RecordingLauncher,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    program_id = await validated(program_rt, ME, start=START)
    run = weekly.run_weekly_reviews
    assert await run(job_ctx.session_factory, job_ctx.replan, AFTER) == 1
    assert await run(job_ctx.session_factory, job_ctx.replan, AFTER) == 0
    [entry] = await _reviews(job_ctx.session_factory)
    assert entry.data["week_start"] == "2026-11-09" and entry.data["state"] == "late"
    assert entry.data["ratio"] == 1.0 and entry.text  # rien de fait : tout en retard
    assert _replans(launcher) == [
        {"program_id": program_id, "trigger": "weekly_review", "review_entry_id": entry.id}
    ]
    # Session close, refusée ou pas : ce bilan ne relance jamais de replanification.
    session_id = await _replan_session(job_ctx.session_factory, program_id)
    await launcher.end(ME, session_id, "cancelled")
    assert await run(job_ctx.session_factory, job_ctx.replan, AFTER) == 0
    assert len(_replans(launcher)) == 1
    assert "Devenir" not in caplog.text and entry.text not in caplog.text


async def test_weekly_review_retries_refused_launch(
    program_rt: ProgramRuntime, job_ctx: JobContext, launcher: RecordingLauncher
) -> None:
    await validated(program_rt, ME, start=START)
    launcher.refuse = True
    assert await weekly.run_weekly_reviews(job_ctx.session_factory, job_ctx.replan, AFTER) == 1
    launcher.refuse = False
    assert await weekly.run_weekly_reviews(job_ctx.session_factory, job_ctx.replan, AFTER) == 0
    assert len(_replans(launcher)) == 1 and len(await _reviews(job_ctx.session_factory)) == 1


async def test_weekly_review_last_week_writes_without_replan(
    program_rt: ProgramRuntime, job_ctx: JobContext, launcher: RecordingLauncher
) -> None:
    await validated(program_rt, ME, start=date(2026, 11, 2))  # semaines du 2 et du 9 : finie
    assert await weekly.run_weekly_reviews(job_ctx.session_factory, job_ctx.replan, AFTER) == 1
    assert _replans(launcher) == []


def _three_weeks() -> PlanDraft:
    plan = sample_plan()
    return plan.model_copy(update={"weeks": [*plan.weeks, plan.weeks[1]]})


async def test_weekly_review_late_twice_offers_options(
    program_rt: ProgramRuntime, job_ctx: JobContext, launcher: RecordingLauncher
) -> None:
    program_id = await validated(program_rt, ME, _three_weeks(), start=date(2026, 11, 2))
    assert await weekly.run_weekly_reviews(job_ctx.session_factory, job_ctx.replan, AFTER) == 1
    [entry] = await _reviews(job_ctx.session_factory)
    assert entry.data["state"] == "late_twice"  # semaine du 2 recalculée : tout en retard
    [payload] = _replans(launcher)
    ctx = await AgentReplanStore(job_ctx.replan).context(
        ME, program_id, trigger="weekly_review", review_entry_id=payload["review_entry_id"],
        available_minutes=None, message=None,
    )  # fmt: skip
    assert ctx.review is not None and ctx.review.state == "late_twice"
    assert ctx.options == ("reduce_scope", "push_deadline")


async def _replan_session(factory: Factory, program_id: str) -> str:
    from app.db.models.agents import AgentSession

    async with factory() as db:
        stmt = select(AgentSession.id).where(
            AgentSession.graph == "replan", AgentSession.subject_id == program_id
        )
        return str((await db.execute(stmt)).scalar_one())
