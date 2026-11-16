"""Relevé hebdomadaire (P10, P13, D160, D173) : du lundi 06:00 locales de la semaine en cours (un
lundi manqué est rattrapé les jours suivants), une fois par semaine ISO **locale**, sauté si un
relevé a déjà été créé cette semaine ou sans poste, repris après une panne de lancement, une panne
pour un compte n'arrête pas les autres."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import select

from app.db.models.agents import AgentSession
from app.db.models.daily import JobRun, RadarRun
from app.features.radar.service.schedule import run_weekly_radar
from app.features.settings.service import SettingsService
from app.scheduler.jobs import market_radar
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.radar.support import ME, OTHER, ROLE, Radar

MONDAY_9H = datetime(2026, 11, 16, 8, 0, tzinfo=UTC)  # lundi 09:00 à Paris, semaine 47


async def _settings(radar: Radar, user: str = ME, **fields: Any) -> None:
    async with radar.factory() as db:
        service = SettingsService(db, user)
        await service.replace((await service.get()).model_copy(update=fields))
        await db.commit()


async def _jobs(radar: Radar, user: str = ME) -> list[JobRun]:
    async with radar.factory() as db:
        stmt = select(JobRun).where(JobRun.user_id == user, JobRun.name == "market_radar")
        return list((await db.execute(stmt.order_by(JobRun.created_at))).scalars())


async def _runs(radar: Radar, user: str = ME) -> list[RadarRun]:
    async with radar.factory() as db:
        stmt = select(RadarRun).where(RadarRun.user_id == user).order_by(RadarRun.created_at)
        return list((await db.execute(stmt)).scalars())


async def test_weekly_once_per_local_week(radar: Radar, launcher: RecordingLauncher) -> None:
    await _settings(radar, radar_role=ROLE, radar_zone="Lyon")
    assert await run_weekly_radar(radar.rt, MONDAY_9H) == 1
    assert await run_weekly_radar(radar.rt, MONDAY_9H + timedelta(minutes=15)) == 0
    assert await run_weekly_radar(radar.rt, MONDAY_9H + timedelta(days=2)) == 0
    [run] = await _runs(radar)
    assert (run.trigger, run.period, run.status, run.role, run.zone) == (
        "schedule",
        "2026-W47",
        "running",
        ROLE,
        "Lyon",
    )
    assert launcher.started == [("market_radar", {"run_id": run.id})]
    [job] = await _jobs(radar)
    assert (job.period, job.status, job.ref_id, job.attempts) == ("2026-W47", "done", run.id, 1)
    assert job.next_due_at == datetime(2026, 11, 23, 5, 0, tzinfo=UTC)  # lundi suivant 06:00 Paris


async def test_weekly_waits_for_monday_six_local(radar: Radar, launcher: RecordingLauncher) -> None:
    await _settings(radar, radar_role=ROLE)
    before_six = datetime(2026, 11, 16, 4, 59, tzinfo=UTC)  # 05:59 à Paris
    assert await run_weekly_radar(radar.rt, before_six) == 0
    assert await _jobs(radar) == [] and launcher.started == []  # rien n'a même été gagné
    assert await run_weekly_radar(radar.rt, before_six + timedelta(minutes=1)) == 1  # 06:00


async def test_weekly_catches_up_on_tuesday_when_monday_was_missed(
    radar: Radar, launcher: RecordingLauncher
) -> None:
    """La pile éteinte le lundi : le mardi (comme tout jour de la semaine) rattrape, une fois."""
    await _settings(radar, radar_role=ROLE)
    tuesday = MONDAY_9H + timedelta(days=1)
    assert await run_weekly_radar(radar.rt, tuesday) == 1
    [run] = await _runs(radar)
    [job] = await _jobs(radar)
    assert (run.period, job.period, job.status) == ("2026-W47", "2026-W47", "done")
    assert (
        await run_weekly_radar(radar.rt, tuesday + timedelta(days=4)) == 0
    )  # dimanche : déjà pris
    assert len(launcher.started) == 1


async def test_weekly_no_second_run_on_tuesday_after_a_monday_success(
    radar: Radar, launcher: RecordingLauncher
) -> None:
    await _settings(radar, radar_role=ROLE)
    assert await run_weekly_radar(radar.rt, MONDAY_9H) == 1
    await _end_run(radar)
    assert await run_weekly_radar(radar.rt, MONDAY_9H + timedelta(days=1)) == 0
    assert len(launcher.started) == 1 and len(await _runs(radar)) == 1


async def test_weekly_failed_monday_run_is_retried_within_the_week(
    radar: Radar, launcher: RecordingLauncher
) -> None:
    await _settings(radar, radar_role=ROLE)
    assert await run_weekly_radar(radar.rt, MONDAY_9H) == 1
    [job] = await _jobs(radar)
    await _kill_session(radar, job.ref_id or "")
    assert await run_weekly_radar(radar.rt, MONDAY_9H + timedelta(days=1)) == 1  # mardi : repris
    [job] = await _jobs(radar)
    assert (job.status, job.attempts) == ("done", 2)
    assert [run.status for run in await _runs(radar)] == ["failed", "running"]


async def test_weekly_run_ended_without_any_analysis_is_retried_within_the_week(
    radar: Radar, launcher: RecordingLauncher
) -> None:
    """Un relevé qui finit `failed` (`analysis_failed`) rouvre le passage de la semaine."""
    await _settings(radar, radar_role=ROLE)
    assert await run_weekly_radar(radar.rt, MONDAY_9H) == 1
    [job] = await _jobs(radar)
    run_id = job.ref_id or ""
    await radar.read(run_id, 2)
    await radar.store.save_extraction(ME, "s", run_id, [], ["p1", "p2"])
    assert (await radar.store.finalize(ME, "s", run_id)).error_code == "analysis_failed"
    await _kill_session(radar, run_id)  # la session échoue avec le parcours
    assert await run_weekly_radar(radar.rt, MONDAY_9H + timedelta(days=1)) == 1
    assert [run.status for run in await _runs(radar)] == ["failed", "running"]
    assert (await _runs(radar))[0].error_code == "analysis_failed"


async def test_weekly_skipped_after_manual_run(radar: Radar, launcher: RecordingLauncher) -> None:
    await _settings(radar, radar_role=ROLE)
    await radar.new_run(status="done", created_at=MONDAY_9H - timedelta(hours=40))  # samedi : 46
    assert await run_weekly_radar(radar.rt, MONDAY_9H) == 1  # la semaine précédente ne compte pas
    await _end_run(radar)
    assert await run_weekly_radar(radar.rt, MONDAY_9H + timedelta(days=7)) == 1
    # Un relevé manuel créé dans la semaine : le passage est sauté.
    next_monday = MONDAY_9H + timedelta(days=14)
    await _end_run(radar)
    await radar.new_run(status="done", created_at=next_monday - timedelta(hours=2))
    assert await run_weekly_radar(radar.rt, next_monday) == 0
    assert (await _jobs(radar))[-1].status == "skipped"
    assert len(launcher.started) == 2


async def _end_run(radar: Radar) -> None:
    """Termine le dernier relevé (fini, session close) pour libérer la place du suivant."""
    async with radar.factory() as db:
        stmt = select(RadarRun).order_by(RadarRun.created_at.desc()).limit(1)
        row = (await db.execute(stmt)).scalar_one()
        row.status = "done"
        await db.commit()


async def test_weekly_not_blocked_by_a_failed_or_dead_run(
    radar: Radar, launcher: RecordingLauncher
) -> None:
    await _settings(radar, radar_role=ROLE)
    early = MONDAY_9H - timedelta(hours=2)
    await radar.new_run(status="failed", created_at=early - timedelta(hours=1))  # échec ce lundi
    await radar.new_run(status="running", created_at=early)  # sans session : mort, corrigé
    assert await run_weekly_radar(radar.rt, MONDAY_9H) == 1
    statuses = [run.status for run in await _runs(radar)]
    assert statuses == ["failed", "failed", "running"]
    assert (await _runs(radar))[1].error_code == "launch_failed"


async def test_weekly_blocked_by_a_live_run(radar: Radar, launcher: RecordingLauncher) -> None:
    await _settings(radar, radar_role=ROLE)
    await radar.open_run(created_at=MONDAY_9H - timedelta(hours=1))
    assert await run_weekly_radar(radar.rt, MONDAY_9H) == 0
    assert (await _jobs(radar))[0].status == "skipped" and launcher.started == []


async def test_weekly_without_a_role_is_skipped(radar: Radar, launcher: RecordingLauncher) -> None:
    assert await run_weekly_radar(radar.rt, MONDAY_9H) == 0
    [job] = await _jobs(radar)
    assert job.status == "skipped" and await _runs(radar) == [] and launcher.started == []


async def test_weekly_period_is_the_local_week_not_the_utc_day(
    radar: Radar, launcher: RecordingLauncher
) -> None:
    """Lundi 06:30 à Auckland est encore dimanche en UTC (semaine ISO 46) : le relevé et le
    passage portent la semaine locale 47. Au même instant, dimanche 12:30 à New York : semaine
    locale 46 (rattrapage de la semaine en cours), jamais la semaine du jour UTC."""
    await _settings(radar, ME, radar_role=ROLE, timezone="Pacific/Auckland")
    await _settings(radar, OTHER, radar_role=ROLE, timezone="America/New_York")
    instant = datetime(2026, 11, 15, 17, 30, tzinfo=UTC)
    assert instant.isocalendar().week == 46
    assert await run_weekly_radar(radar.rt, instant) == 2
    [run], [job] = await _runs(radar), await _jobs(radar)
    assert (run.period, job.period) == ("2026-W47", "2026-W47")  # lundi 06:30 à Auckland
    [york], [york_job] = await _runs(radar, OTHER), await _jobs(radar, OTHER)
    assert (york.period, york_job.period) == ("2026-W46", "2026-W46")  # dimanche à New York
    # Dimanche 23:30 à New York est déjà lundi en UTC (semaine 47) : le passage de New York reste
    # celui de sa semaine locale, il n'en gagne pas un second.
    assert await run_weekly_radar(radar.rt, datetime(2026, 11, 16, 4, 30, tzinfo=UTC)) == 0
    assert len(await _jobs(radar, OTHER)) == 1


async def test_weekly_launch_failure_is_recorded_then_retried(
    radar: Radar, launcher: RecordingLauncher
) -> None:
    await _settings(radar, radar_role=ROLE)
    launcher.refuse = True
    assert await run_weekly_radar(radar.rt, MONDAY_9H) == 0
    [job] = await _jobs(radar)
    assert (job.status, job.error_code) == ("failed", "engine_unavailable")
    assert [run.status for run in await _runs(radar)] == ["failed"]
    launcher.refuse = False
    assert await run_weekly_radar(radar.rt, MONDAY_9H + timedelta(minutes=15)) == 1
    [job] = await _jobs(radar)
    assert (job.status, job.attempts) == ("done", 2)


async def test_weekly_one_failure_does_not_stop_the_others(radar: Radar) -> None:
    class FailsFirst(RecordingLauncher):
        async def start(self, user_id: str, *args: Any, **kwargs: Any) -> str:
            if user_id == ME:
                raise RuntimeError("panne")
            return await super().start(user_id, *args, **kwargs)

    radar.rt.launcher = FailsFirst(radar.factory)
    await _settings(radar, ME, radar_role=ROLE)
    await _settings(radar, OTHER, radar_role="Autre poste")
    assert await run_weekly_radar(radar.rt, MONDAY_9H) == 1
    assert [job.status for job in await _jobs(radar, ME)] == ["failed"]
    assert [job.error_code for job in await _jobs(radar, ME)] == ["RuntimeError"]
    assert [job.status for job in await _jobs(radar, OTHER)] == ["done"]


async def test_the_scheduled_task_calls_the_weekly_run_with_utc_now(
    radar: Radar, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[object, datetime]] = []

    async def spy(rt: object, now: datetime) -> int:
        seen.append((rt, now))
        return 0

    monkeypatch.setattr(market_radar, "run_weekly_radar", spy)
    await market_radar.run(SimpleNamespace(daily=SimpleNamespace(radar=radar.rt)))  # type: ignore[arg-type]
    [(rt, now)] = seen
    assert rt is radar.rt and now.tzinfo is not None


async def _kill_session(radar: Radar, run_id: str, status: str = "failed") -> None:
    async with radar.factory() as db:
        stmt = select(AgentSession).where(AgentSession.subject_id == run_id)
        (await db.execute(stmt)).scalar_one().status = status
        await db.commit()


async def test_weekly_pass_is_reopened_when_its_run_failed_within_the_attempts_cap(
    radar: Radar, launcher: RecordingLauncher
) -> None:
    """Le passage est `done` au lancement : si le relevé échoue ensuite (session morte), le passage
    suivant le reprend, 3 essais au plus par semaine."""
    await _settings(radar, radar_role=ROLE)
    for attempt in (1, 2, 3):
        now = MONDAY_9H + timedelta(minutes=15 * attempt)
        assert await run_weekly_radar(radar.rt, now) == 1
        [job] = await _jobs(radar)
        assert (job.status, job.attempts) == ("done", attempt)
        assert await run_weekly_radar(radar.rt, now) == 0  # le relevé vit : rien de plus
        await _kill_session(radar, job.ref_id or "")
    assert await run_weekly_radar(radar.rt, MONDAY_9H + timedelta(hours=2)) == 0
    [job] = await _jobs(radar)
    assert (job.status, job.attempts, job.error_code) == ("failed", 3, "session_failed")
    assert [run.status for run in await _runs(radar)] == ["failed"] * 3
    assert len(launcher.started) == 3
    # La semaine suivante repart à zéro.
    assert await run_weekly_radar(radar.rt, MONDAY_9H + timedelta(days=7)) == 1


async def test_weekly_pass_whose_run_finished_is_left_alone(
    radar: Radar, launcher: RecordingLauncher
) -> None:
    await _settings(radar, radar_role=ROLE)
    assert await run_weekly_radar(radar.rt, MONDAY_9H) == 1
    [run] = await _runs(radar)
    await _kill_session(radar, run.id, "completed")  # fini normalement : `done` (par la fin)
    await _end_run(radar)
    assert await run_weekly_radar(radar.rt, MONDAY_9H + timedelta(hours=1)) == 0
    assert (await _jobs(radar))[0].attempts == 1 and len(launcher.started) == 1


async def test_weekly_pass_is_not_reopened_when_january_cancelled_the_run(
    radar: Radar, launcher: RecordingLauncher
) -> None:
    """Une session annulée par January elle-même (`session_cancelled`) n'est jamais relancée,
    contrairement à une session en échec."""
    await _settings(radar, radar_role=ROLE)
    assert await run_weekly_radar(radar.rt, MONDAY_9H) == 1
    [job] = await _jobs(radar)
    await _kill_session(radar, job.ref_id or "", "cancelled")
    for minutes in (15, 30, 45):
        assert await run_weekly_radar(radar.rt, MONDAY_9H + timedelta(minutes=minutes)) == 0
    [job] = await _jobs(radar)
    assert (job.status, job.attempts) == ("done", 1) and len(launcher.started) == 1
    [run] = await _runs(radar)
    assert (run.status, run.error_code) == ("failed", "session_cancelled")
