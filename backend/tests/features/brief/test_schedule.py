"""Tâche du matin (P12, P13, D162) : après l'heure du brief chez January seulement, une fois par
jour local, sautée si le brief a été créé à l'ouverture, reprise après une panne ; une panne pour
un compte n'arrête pas les autres. Règle `brief_due` les jours de changement d'heure."""

import logging
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from app.db.models.learning import Goal
from app.features.brief.service import schedule
from app.features.brief.service.ensure import ensure_today
from app.features.brief.service.rules import brief_day, brief_due
from app.features.brief.service.runtime import BriefRuntime
from app.features.brief.service.schedule import run_daily_briefs
from app.features.settings.service import SettingsService
from app.scheduler.jobs import daily_brief
from app.scheduler.registry import JOBS
from tests.features.brief.conftest import OTHER, Env
from tests.features.brief.support import add_user, brief_sessions, briefs, jobs
from tests.support.onboarding import finish_first_launch

PARIS = ZoneInfo("Europe/Paris")
OPENING = datetime(2026, 11, 17, 5, 30, tzinfo=UTC)  # 06 h 30 à Paris, avant l'heure du brief
BEFORE = datetime(2026, 11, 17, 5, 55, tzinfo=UTC)  # 06 h 55
AFTER = datetime(2026, 11, 17, 6, 5, tzinfo=UTC)  # 07 h 05


async def _brief_time(env: Env, hhmm: str, user: str | None = None) -> None:
    async with env.rt.session_factory() as db:
        service = SettingsService(db, user or env.user_id)
        await service.replace((await service.get()).model_copy(update={"brief_time": hhmm}))
        await db.commit()


async def test_job_creates_after_hour_only(env: Env, rt: BriefRuntime) -> None:
    env.at(BEFORE)
    assert await run_daily_briefs(rt, BEFORE) == 0  # 6 h 55 : rien, pas même un passage gagné
    assert await briefs(env) == [] and await jobs(env) == []
    env.at(AFTER)
    assert await run_daily_briefs(rt, AFTER) == 1  # 7 h 05
    [brief] = await briefs(env)
    assert brief.origin == "schedule" and brief.day.isoformat() == "2026-11-17"
    [job] = await jobs(env)
    assert (job.period, job.status, job.ref_id, job.attempts) == (
        "2026-11-17",
        "done",
        brief.id,
        1,
    )
    assert job.next_due_at == datetime(2026, 11, 18, 6, 0, tzinfo=UTC)  # demain 07 h 00 à Paris
    assert env.launcher.started == [("daily_brief", {"brief_id": brief.id})]


async def test_job_after_opening_does_nothing(env: Env, rt: BriefRuntime) -> None:
    env.at(OPENING)
    opened, created = await ensure_today(rt, env.user_id, origin="opening")  # ouverture 6 h 30
    assert created is True
    env.at(AFTER)
    assert await run_daily_briefs(rt, AFTER) == 0  # la tâche de 7 h 05 ne crée rien
    [brief] = await briefs(env)
    assert brief.id == opened.id and brief.origin == "opening"
    [job] = await jobs(env)
    assert (job.status, job.ref_id) == ("skipped", opened.id)  # passage sauté, avec le brief
    assert await brief_sessions(env) == 1  # une seule session


async def test_job_runs_once_a_day_even_every_ten_minutes(env: Env, rt: BriefRuntime) -> None:
    env.at(AFTER)
    assert await run_daily_briefs(rt, AFTER) == 1
    later = AFTER + timedelta(minutes=10)
    env.at(later)
    assert await run_daily_briefs(rt, later) == 0
    assert len(await jobs(env)) == 1 and len(await briefs(env)) == 1
    tomorrow = AFTER + timedelta(days=1)  # le lendemain, un nouveau jour local
    env.at(tomorrow)
    assert await run_daily_briefs(rt, tomorrow) == 1
    assert [j.period for j in await jobs(env)] == ["2026-11-17", "2026-11-18"]


async def test_job_failure_is_retried_at_the_next_pass(
    env: Env, rt: BriefRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    env.at(AFTER)
    real = schedule.ensure_today

    async def broken(*args: object, **kwargs: object) -> object:
        raise RuntimeError("panne : donnée secrète")

    monkeypatch.setattr(schedule, "ensure_today", broken)
    assert await run_daily_briefs(rt, AFTER) == 0
    [job] = await jobs(env)
    assert (job.status, job.error_code, job.attempts) == ("failed", "RuntimeError", 1)
    monkeypatch.setattr(schedule, "ensure_today", real)
    assert await run_daily_briefs(rt, AFTER + timedelta(minutes=10)) == 1
    [job] = await jobs(env)
    assert (job.status, job.attempts) == ("done", 2)


async def test_one_account_failing_does_not_stop_the_others(
    env: Env, rt: BriefRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    await add_user(env, OTHER)
    env.at(AFTER)
    real = schedule.ensure_today

    async def selective(rt_: BriefRuntime, user_id: str, **kwargs: object) -> object:
        if user_id == env.user_id:
            raise RuntimeError("panne")
        return await real(rt_, user_id, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(schedule, "ensure_today", selective)
    assert await run_daily_briefs(rt, AFTER) == 1
    assert await briefs(env) == [] and len(await briefs(env, OTHER)) == 1


async def test_job_waits_for_the_first_launch_then_works(env: Env, rt: BriefRuntime) -> None:
    """D197 : un compte dont le premier lancement n'est pas fini ne prend aucun passage, ne lance
    aucune session ; le premier passage après la fin du premier lancement le traite."""
    await add_user(env, OTHER, onboarded=False)
    await finish_first_launch(rt.session_factory, OTHER, done=False)  # la ligne `false` existe
    env.at(AFTER)
    assert await run_daily_briefs(rt, AFTER) == 1  # seul le compte au premier lancement fini
    assert await briefs(env, OTHER) == [] and await jobs(env, OTHER) == []
    assert env.launcher.started == [("daily_brief", {"brief_id": (await briefs(env))[0].id})]
    await finish_first_launch(rt.session_factory, OTHER)  # il termine l'accueil
    later = AFTER + timedelta(minutes=10)
    env.at(later)
    assert await run_daily_briefs(rt, later) == 1
    [brief] = await briefs(env, OTHER)
    [job] = await jobs(env, OTHER)
    assert (job.status, job.ref_id, job.attempts) == ("done", brief.id, 1)


async def test_job_skips_a_new_account_without_settings_quietly(
    env: Env, rt: BriefRuntime, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    await add_user(env, OTHER, onboarded=False)  # ni ligne de réglages ni donnée
    env.at(AFTER)
    assert await run_daily_briefs(rt, AFTER) == 1
    assert await briefs(env, OTHER) == [] and await jobs(env, OTHER) == []
    above_debug = [
        r for r in caplog.records if r.levelno > logging.INFO and OTHER in r.getMessage()
    ]
    assert above_debug == []


async def test_job_keeps_an_old_account_with_data_working(env: Env, rt: BriefRuntime) -> None:
    """Un compte d'avant la phase 9 (réglages anciens que la migration marque faits, ou sans ligne
    mais avec un objectif) reste traité comme `GET /settings` le juge (D183)."""
    await add_user(env, OTHER, onboarded=False)
    async with rt.session_factory() as db:
        db.add(Goal(user_id=OTHER, text="Devenir ingénieure en apprentissage automatique"))
        await db.commit()
    env.at(AFTER)
    assert await run_daily_briefs(rt, AFTER) == 2
    assert len(await briefs(env, OTHER)) == 1


async def test_job_follows_each_accounts_own_brief_time(env: Env, rt: BriefRuntime) -> None:
    await add_user(env, OTHER)
    await _brief_time(env, "09:00", OTHER)  # l'autre veut son brief à 9 h (8 h UTC) : pas encore
    env.at(AFTER)
    assert await run_daily_briefs(rt, AFTER) == 1
    assert len(await briefs(env)) == 1 and await briefs(env, OTHER) == []


async def test_job_day_is_the_local_day(env: Env, rt: BriefRuntime) -> None:
    await _brief_time(env, "00:15")
    moment = datetime(2026, 11, 16, 23, 20, tzinfo=UTC)  # 00 h 20 à Paris : déjà le 17
    env.at(moment)
    assert await run_daily_briefs(rt, moment) == 1
    assert (await jobs(env))[0].period == "2026-11-17"
    assert (await briefs(env))[0].day.isoformat() == "2026-11-17"


async def test_job_on_the_spring_dst_day_with_a_skipped_hour(env: Env, rt: BriefRuntime) -> None:
    await _brief_time(env, "02:30")  # le 29 mars 2026, 02:30 n'existe pas à Paris
    before = datetime(2026, 3, 29, 1, 29, tzinfo=UTC)
    exact = datetime(2026, 3, 29, 1, 30, tzinfo=UTC)
    env.at(before)
    assert await run_daily_briefs(rt, before) == 0
    env.at(exact)
    assert await run_daily_briefs(rt, exact) == 1
    [job] = await jobs(env)
    assert job.period == "2026-03-29"
    assert job.next_due_at == datetime(2026, 3, 30, 0, 30, tzinfo=UTC)  # 02:30 à Paris, UTC+2


def test_brief_due_on_the_spring_dst_day() -> None:
    """Le 29 mars 2026 à Paris, 02:00 saute à 03:00 : 02:30 se lit avec le décalage d'avant
    (UTC+1), soit 01:30 UTC, comme `local_moment`."""
    assert brief_day(datetime(2026, 3, 29, 0, 59, tzinfo=UTC), PARIS).isoformat() == "2026-03-29"
    assert not brief_due(datetime(2026, 3, 29, 1, 29, tzinfo=UTC), PARIS, "02:30")
    assert brief_due(datetime(2026, 3, 29, 1, 30, tzinfo=UTC), PARIS, "02:30")
    assert brief_due(datetime(2026, 3, 29, 1, 0, tzinfo=UTC), PARIS, "02:00")  # l'heure sautée


def test_brief_due_on_the_autumn_dst_day() -> None:
    """Le 25 octobre 2026 à Paris, 02:00 à 03:00 existent deux fois : 02:30 se lit à sa première
    occurrence (UTC+2), soit 00:30 UTC. Le jour local reste le 25 de 22:00 UTC la veille à
    22:59 UTC."""
    assert brief_day(datetime(2026, 10, 24, 22, 0, tzinfo=UTC), PARIS).isoformat() == "2026-10-25"
    assert not brief_due(datetime(2026, 10, 25, 0, 29, tzinfo=UTC), PARIS, "02:30")
    assert brief_due(datetime(2026, 10, 25, 0, 30, tzinfo=UTC), PARIS, "02:30")
    assert brief_due(datetime(2026, 10, 25, 1, 45, tzinfo=UTC), PARIS, "02:30")  # la 2e occurrence
    assert brief_day(datetime(2026, 10, 25, 22, 59, tzinfo=UTC), PARIS).isoformat() == "2026-10-25"
    assert brief_day(datetime(2026, 10, 25, 23, 0, tzinfo=UTC), PARIS).isoformat() == "2026-10-26"


async def test_job_on_the_autumn_dst_day_runs_once(env: Env, rt: BriefRuntime) -> None:
    await _brief_time(env, "02:30")
    first = datetime(2026, 10, 25, 0, 30, tzinfo=UTC)  # la première 02:30
    env.at(first)
    assert await run_daily_briefs(rt, first) == 1
    second = datetime(2026, 10, 25, 1, 30, tzinfo=UTC)  # la seconde 02:30 : rien de plus
    env.at(second)
    assert await run_daily_briefs(rt, second) == 0
    assert len(await briefs(env)) == 1 and len(await jobs(env)) == 1


async def test_the_task_unpacks_its_context_and_reads_the_clock(
    rt: BriefRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[object, datetime]] = []

    async def spy(runtime: object, now: datetime) -> int:
        seen.append((runtime, now))
        return 0

    monkeypatch.setattr(daily_brief, "run_daily_briefs", spy)
    await daily_brief.run(SimpleNamespace(daily=SimpleNamespace(brief=rt)))  # type: ignore[arg-type]
    [(runtime, now)] = seen
    assert runtime is rt and now.tzinfo is not None


def test_the_task_runs_every_ten_minutes_and_at_startup() -> None:
    [spec] = [job for job in JOBS if job.name == "daily_brief"]
    assert spec.every == timedelta(minutes=10) and spec.at_startup
