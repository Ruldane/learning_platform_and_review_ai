"""Rafraîchissement ATS (P14, D158) : toutes les 30 jours, par compte, une session `web_research`
(requête fixe, sujet `ats_refresh`) ; un passage par jour local au plus (registre) ; une panne de
lancement est rangée sous son code ; la revue de CV lit les sources retenues de la dernière
session terminée il y a moins de 60 jours (3 au plus)."""

import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.agents.tools.cv_review_port import AtsUpdate
from app.core.clock import local_today
from app.db.models.accounts import User
from app.db.models.agents import AgentSession
from app.db.models.daily import JobRun
from app.db.models.research import Source
from app.features.cv.service.ats_refresh import ATS_QUERY, run_ats_refresh
from app.features.cv.service.review_store import AgentCvReviewStore
from app.features.cv.service.reviews import start_review
from app.features.cv.service.runtime import CvRuntime
from app.features.ledger.service.ledger import claim, finish
from app.features.ledger.service.periods import day_period, week_period
from app.features.settings.service import SettingsService
from tests.features.cv.reviews_support import ready_posting, ready_template, validated_profile
from tests.features.cv.templates_support import ME
from tests.features.lessons.conftest import OTHER, RecordingLauncher
from tests.features.program.support import Factory
from tests.support.onboarding import finish_first_launch

NOW = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)


async def _users(factory: Factory, *ids: str, onboarded: bool = True) -> None:
    async with factory() as db:
        db.add_all([User(id=one, user_id=one) for one in ids])
        await db.commit()
    if onboarded:  # le planificateur ne traite que les comptes au premier lancement fini (D197)
        await finish_first_launch(factory, *ids)


async def _done(factory: Factory, user: str, at: datetime) -> None:
    """Un passage `ats_refresh` terminé à `at` (période : son jour UTC)."""
    async with factory() as db:
        got = await claim(db, user, "ats_refresh", day_period(at.date()), at)
        assert got is not None
        await finish(db, user, got.run_id, attempt=1, status="done", now=at, ref_id="s-old")
        await db.commit()


async def _rows(factory: Factory, user: str) -> list[JobRun]:
    async with factory() as db:
        stmt = select(JobRun).where(JobRun.user_id == user, JobRun.name == "ats_refresh")
        return list((await db.execute(stmt.order_by(JobRun.created_at))).scalars())


async def test_ats_refresh_due_every_thirty_days(
    db_session_factory: Factory, launcher: RecordingLauncher
) -> None:
    await _users(db_session_factory, ME)
    await _done(db_session_factory, ME, NOW - timedelta(days=29))
    assert await run_ats_refresh(db_session_factory, launcher, NOW) == 0
    assert launcher.started == []
    await _users(db_session_factory, OTHER)
    await _done(db_session_factory, OTHER, NOW - timedelta(days=30))
    assert await run_ats_refresh(db_session_factory, launcher, NOW) == 1
    assert launcher.started == [("web_research", {"query": ATS_QUERY})]
    async with db_session_factory() as db:
        [session] = (await db.execute(select(AgentSession))).scalars()
    assert session.user_id == OTHER and session.subject_type == "ats_refresh"
    done = (await _rows(db_session_factory, OTHER))[-1]
    assert done.status == "done" and done.ref_id == session.id
    assert done.next_due_at == NOW + timedelta(days=30) and done.period == "2026-11-16"


async def test_ats_refresh_first_run_and_once_a_day(
    db_session_factory: Factory, launcher: RecordingLauncher
) -> None:
    await _users(db_session_factory, ME, OTHER)
    assert await run_ats_refresh(db_session_factory, launcher, NOW) == 2
    assert await run_ats_refresh(db_session_factory, launcher, NOW + timedelta(hours=6)) == 0
    assert len(launcher.started) == 2


async def test_ats_refresh_waits_for_the_first_launch(
    db_session_factory: Factory, launcher: RecordingLauncher
) -> None:
    """D197 : un compte neuf ne prend aucun passage ni session web ; il est traité au premier
    passage qui suit la fin de son premier lancement."""
    await _users(db_session_factory, ME, onboarded=False)
    assert await run_ats_refresh(db_session_factory, launcher, NOW) == 0
    assert launcher.started == [] and await _rows(db_session_factory, ME) == []
    await finish_first_launch(db_session_factory, ME)
    assert await run_ats_refresh(db_session_factory, launcher, NOW + timedelta(minutes=5)) == 1
    assert [row.status for row in await _rows(db_session_factory, ME)] == ["done"]


async def test_ats_refresh_launch_failure_recorded(
    db_session_factory: Factory,
    launcher: RecordingLauncher,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    await _users(db_session_factory, ME)
    launcher.refuse = True
    assert await run_ats_refresh(db_session_factory, launcher, NOW) == 0
    [row] = await _rows(db_session_factory, ME)
    assert row.status == "failed" and row.error_code == "engine_unavailable"
    assert row.ref_id is None
    assert "Le moteur d'agents" not in "\n".join(r.getMessage() for r in caplog.records)
    launcher.refuse = False  # repris au passage suivant, même jour (essai 2)
    assert await run_ats_refresh(db_session_factory, launcher, NOW + timedelta(hours=6)) == 1
    [row] = await _rows(db_session_factory, ME)
    assert row.status == "done" and row.attempts == 2


async def test_ats_refresh_unexpected_error_keeps_type_only(
    db_session_factory: Factory, launcher: RecordingLauncher
) -> None:
    class Boom(Exception):
        pass

    class Failing(RecordingLauncher):
        async def start(self, *args: object, **kwargs: object) -> str:
            raise Boom("Société Fictive")

    await _users(db_session_factory, ME)
    assert await run_ats_refresh(db_session_factory, Failing(db_session_factory), NOW) == 0
    [row] = await _rows(db_session_factory, ME)
    assert row.status == "failed" and row.error_code == "Boom"


async def test_ats_refresh_one_failure_does_not_stop_the_others(
    db_session_factory: Factory, launcher: RecordingLauncher
) -> None:
    class FailsFirst(RecordingLauncher):
        async def start(self, user_id: str, *args: object, **kwargs: object) -> str:
            if user_id == ME:
                raise RuntimeError("panne")
            return await super().start(user_id, *args, **kwargs)  # type: ignore[arg-type]

    await _users(db_session_factory, ME, OTHER)
    spy = FailsFirst(db_session_factory)
    assert await run_ats_refresh(db_session_factory, spy, NOW) == 1
    assert [row.status for row in await _rows(db_session_factory, ME)] == ["failed"]
    assert [row.status for row in await _rows(db_session_factory, OTHER)] == ["done"]


async def test_ats_refresh_period_is_the_local_day(
    db_session_factory: Factory, launcher: RecordingLauncher
) -> None:
    """Dimanche 23 h 30 à New York est déjà lundi UTC : le passage porte le jour local (la
    semaine ISO locale suit `local_today`, jamais `now.date()`)."""
    paris_late = datetime(2026, 11, 15, 23, 30, tzinfo=UTC)  # lundi 16, 00 h 30 à Paris
    new_york = datetime(2026, 11, 16, 4, 30, tzinfo=UTC)  # dimanche 15, 23 h 30 à New York
    await _users(db_session_factory, ME, OTHER)
    async with db_session_factory() as db:
        settings = SettingsService(db, OTHER)
        stored = await settings.get()
        await settings.replace(stored.model_copy(update={"timezone": "America/New_York"}))
        await db.commit()
    await run_ats_refresh(db_session_factory, launcher, paris_late)
    [paris] = await _rows(db_session_factory, ME)
    assert paris.period == "2026-11-16"  # et non le jour UTC, 2026-11-15
    await run_ats_refresh(db_session_factory, launcher, new_york)
    [york] = await _rows(db_session_factory, OTHER)
    local = local_today(ZoneInfo("America/New_York"), new_york)
    assert york.period == "2026-11-15" == day_period(local)
    assert week_period(local) == "2026-W46"  # la semaine ISO locale : celle du dimanche
    assert week_period(new_york.date()) == "2026-W47"  # le jour UTC donnerait la mauvaise


# --- La revue de CV lit les mises à jour récentes -------------------------------------------


async def _refresh_session(
    rt: CvRuntime, user: str, *, ended: datetime, status: str = "completed", kept: int = 4
) -> str:
    async with rt.session_factory() as db:
        session = AgentSession(
            user_id=user,
            graph="web_research",
            status=status,
            input={"query": ATS_QUERY},
            subject_type="ats_refresh",
            updated_at=ended,
        )
        db.add(session)
        await db.flush()
        for number in range(kept + 1):
            kind_kept = number < kept
            db.add(
                Source(
                    user_id=user,
                    session_id=session.id,
                    url=f"https://exemple.invalid/{session.id[:4]}/{number}",
                    url_hash=f"{session.id}-{number}",
                    title=f"Titre {number}",
                    status="ok",
                    verdict="kept" if kind_kept else "rejected",
                    score=90 - number,
                    summary=f"Résumé {number}",
                    published="2026-10-30" if number == 0 else None,
                )
            )
        await db.commit()
        return session.id


async def _review(rt: CvRuntime) -> str:
    await ready_template(rt, ME)
    await validated_profile(rt, ME)
    posting_id = await ready_posting(rt, ME)
    return (await start_review(rt, ME, posting_id)).review_id


async def test_review_context_has_recent_ats_updates(cv_runtime: CvRuntime) -> None:
    review_id = await _review(cv_runtime)
    store = AgentCvReviewStore(cv_runtime)
    assert (await store.context(ME, review_id)).ats_updates == []
    now = cv_runtime.now()
    await _refresh_session(cv_runtime, ME, ended=now - timedelta(days=61))  # trop vieille
    await _refresh_session(cv_runtime, ME, ended=now - timedelta(days=1), status="running")
    await _refresh_session(cv_runtime, ME, ended=now - timedelta(days=1), status="failed")
    await _refresh_session(cv_runtime, OTHER, ended=now - timedelta(days=1))  # pas à elle
    assert (await store.context(ME, review_id)).ats_updates == []
    older = await _refresh_session(cv_runtime, ME, ended=now - timedelta(days=40))
    newer = await _refresh_session(cv_runtime, ME, ended=now - timedelta(days=10))
    assert older != newer
    updates = (await store.context(ME, review_id)).ats_updates
    assert [u.title for u in updates] == ["Titre 0", "Titre 1", "Titre 2"]  # 3 « kept » au plus
    assert updates[0] == AtsUpdate(
        title="Titre 0",
        url=f"https://exemple.invalid/{newer[:4]}/0",
        summary="Résumé 0",
        published="2026-10-30",
    )
    assert all(u.url.split("/")[3] == newer[:4] for u in updates)  # la plus récente seulement


async def test_latest_refresh_without_kept_sources_does_not_hide_an_older_one(
    cv_runtime: CvRuntime,
) -> None:
    review_id = await _review(cv_runtime)
    store = AgentCvReviewStore(cv_runtime)
    now = cv_runtime.now()
    older = await _refresh_session(cv_runtime, ME, ended=now - timedelta(days=30), kept=3)
    await _refresh_session(cv_runtime, ME, ended=now - timedelta(days=2), kept=0)  # rien retenu
    updates = (await store.context(ME, review_id)).ats_updates
    assert [u.title for u in updates] == ["Titre 0", "Titre 1", "Titre 2"]
    assert all(u.url.split("/")[3] == older[:4] for u in updates)


# --- Une session échouée compte comme un rafraîchissement non fait ---------------------------


async def _end_session(factory: Factory, session_id: str, status: str) -> None:
    async with factory() as db:
        row = (await db.execute(select(AgentSession).where(AgentSession.id == session_id))).one()[0]
        row.status = status
        await db.commit()


async def test_done_pass_with_a_failed_session_is_retried_within_the_attempts_cap(
    db_session_factory: Factory, launcher: RecordingLauncher
) -> None:
    await _users(db_session_factory, ME)
    for attempt in (1, 2, 3):
        assert await run_ats_refresh(db_session_factory, launcher, NOW) == 1
        [row] = await _rows(db_session_factory, ME)
        assert row.status == "done" and row.attempts == attempt
        await _end_session(db_session_factory, row.ref_id or "", "failed")
    # Trois essais, trois sessions échouées : le plafond tient, rien de plus ce jour-là.
    assert await run_ats_refresh(db_session_factory, launcher, NOW) == 0
    [row] = await _rows(db_session_factory, ME)
    assert row.status == "failed" and row.attempts == 3 and row.error_code == "session_failed"
    assert len(launcher.started) == 3
    # Le lendemain, une nouvelle période : un nouveau passage.
    assert await run_ats_refresh(db_session_factory, launcher, NOW + timedelta(days=1)) == 1


async def test_done_pass_with_a_running_or_completed_session_is_not_retried(
    db_session_factory: Factory, launcher: RecordingLauncher
) -> None:
    await _users(db_session_factory, ME)
    assert await run_ats_refresh(db_session_factory, launcher, NOW) == 1
    [row] = await _rows(db_session_factory, ME)
    assert await run_ats_refresh(db_session_factory, launcher, NOW + timedelta(hours=6)) == 0
    await _end_session(db_session_factory, row.ref_id or "", "completed")
    assert await run_ats_refresh(db_session_factory, launcher, NOW + timedelta(hours=12)) == 0
    assert len(launcher.started) == 1
