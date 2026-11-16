"""Registre des passages (P13, D158) : `claim` atomique par `(utilisateur, tâche, période)`,
reprise d'un passage en échec ou périmé (3 essais), `finish` et `fail`, lectures par utilisateur.
Plusieurs sessions réelles sur le fichier SQLite de test : un seul gagnant."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.accounts import User
from app.db.models.daily import JobRun
from app.features.ledger.service.ledger import (
    Claim,
    claim,
    fail,
    finish,
    last_done,
    recent_failures,
    reopen,
    user_ids,
)

NOW = datetime(2026, 11, 16, 7, 0, tzinfo=UTC)
ME, OTHER = "moi", "autre"
Factory = async_sessionmaker[AsyncSession]


async def _claim(
    factory: Factory, user: str = ME, period: str = "2026-11-16", now: datetime = NOW
) -> Claim | None:
    async with factory() as db:
        got = await claim(db, user, "daily_brief", period, now)
        await db.commit()
    return got


async def _fail(
    factory: Factory, run_id: str, code: str = "engine_unavailable", attempt: int = 1
) -> None:
    async with factory() as db:
        await fail(db, ME, run_id, attempt=attempt, code=code, now=NOW)
        await db.commit()


async def _row(factory: Factory, user: str = ME, period: str = "2026-11-16") -> JobRun:
    async with factory() as db:
        stmt = select(JobRun).where(JobRun.user_id == user, JobRun.period == period)
        return (await db.execute(stmt)).scalar_one()


async def test_claim_once_per_period(db_session_factory: Factory) -> None:
    first = await _claim(db_session_factory)
    assert first is not None and first.attempt == 1
    assert await _claim(db_session_factory) is None
    other_period = await _claim(db_session_factory, period="2026-11-17")
    other_user = await _claim(db_session_factory, user=OTHER)
    assert other_period is not None and other_user is not None


async def test_concurrent_claims_one_winner(db_session_factory: Factory) -> None:
    results = await asyncio.gather(*[_claim(db_session_factory) for _ in range(5)])
    assert sum(r is not None for r in results) == 1
    async with db_session_factory() as db:
        count = (await db.execute(select(func.count()).select_from(JobRun))).scalar_one()
    assert count == 1


async def test_concurrent_reclaims_of_failed_one_winner(db_session_factory: Factory) -> None:
    first = await _claim(db_session_factory)
    assert first is not None
    await _fail(db_session_factory, first.run_id)
    later = NOW + timedelta(minutes=5)
    results = await asyncio.gather(*[_claim(db_session_factory, now=later) for _ in range(5)])
    winners = [r for r in results if r is not None]
    assert len(winners) == 1 and winners[0].attempt == 2 and winners[0].run_id == first.run_id


async def test_failed_is_reclaimed_until_three_attempts(db_session_factory: Factory) -> None:
    attempts = []
    for number in range(1, 5):
        got = await _claim(db_session_factory, now=NOW + timedelta(minutes=number))
        if got is None:
            break
        attempts.append(got.attempt)
        await _fail(db_session_factory, got.run_id, attempt=got.attempt)
    assert attempts == [1, 2, 3]
    row = await _row(db_session_factory)
    assert row.status == "failed" and row.attempts == 3 and row.error_code == "engine_unavailable"


async def test_running_reclaimed_only_when_stale(db_session_factory: Factory) -> None:
    first = await _claim(db_session_factory)
    assert first is not None
    assert await _claim(db_session_factory, now=NOW + timedelta(minutes=29)) is None
    again = await _claim(db_session_factory, now=NOW + timedelta(minutes=31))
    assert again == Claim(run_id=first.run_id, attempt=2)
    row = await _row(db_session_factory)
    assert row.status == "running" and row.started_at == NOW + timedelta(minutes=31)
    assert row.error_code is None and row.finished_at is None


async def test_stale_running_out_of_attempts_is_abandoned(db_session_factory: Factory) -> None:
    clock = NOW
    for _ in range(3):
        assert await _claim(db_session_factory, now=clock) is not None
        clock += timedelta(minutes=31)
    assert await _claim(db_session_factory, now=clock) is None
    row = await _row(db_session_factory)
    assert row.status == "failed" and row.error_code == "abandoned" and row.attempts == 3
    async with db_session_factory() as db:
        [view] = await recent_failures(db, ME, None, 10)
    assert view.error_code == "abandoned"


async def test_done_and_skipped_are_never_reclaimed(db_session_factory: Factory) -> None:
    done = await _claim(db_session_factory)
    skipped = await _claim(db_session_factory, period="2026-11-17")
    assert done is not None and skipped is not None
    async with db_session_factory() as db:
        await finish(db, ME, done.run_id, attempt=1, status="done", now=NOW)
        await finish(db, ME, skipped.run_id, attempt=1, status="skipped", now=NOW)
        await db.commit()
    later = NOW + timedelta(days=2)
    assert await _claim(db_session_factory, now=later) is None
    assert await _claim(db_session_factory, period="2026-11-17", now=later) is None


async def test_finish_records_next_due(db_session_factory: Factory) -> None:
    got = await _claim(db_session_factory)
    assert got is not None
    end, due = NOW + timedelta(minutes=2), NOW + timedelta(days=30)
    async with db_session_factory() as db:
        await finish(
            db, ME, got.run_id, attempt=1, status="done", now=end, ref_id="s-1", next_due_at=due
        )
        await db.commit()
    row = await _row(db_session_factory)
    assert (row.status, row.finished_at, row.ref_id, row.next_due_at) == ("done", end, "s-1", due)
    async with db_session_factory() as db:
        view = await last_done(db, ME, "daily_brief")
        assert view is not None and view.run_id == got.run_id and view.next_due_at == due
        assert view.finished_at == end and view.ref_id == "s-1" and view.period == "2026-11-16"
        assert await last_done(db, OTHER, "daily_brief") is None
        assert await last_done(db, ME, "market_radar") is None


async def test_finish_and_fail_touch_only_the_owner_and_running_rows(
    db_session_factory: Factory,
) -> None:
    got = await _claim(db_session_factory)
    assert got is not None
    async with db_session_factory() as db:
        await finish(db, OTHER, got.run_id, attempt=1, status="done", now=NOW)  # pas à elle
        await fail(db, OTHER, got.run_id, attempt=1, code="x", now=NOW)
        await db.commit()
    assert (await _row(db_session_factory)).status == "running"
    async with db_session_factory() as db:
        await finish(db, ME, got.run_id, attempt=1, status="done", now=NOW)
        await fail(db, ME, got.run_id, attempt=1, code="x", now=NOW)  # fini : ne retombe pas
        await db.commit()
    row = await _row(db_session_factory)
    assert row.status == "done" and row.error_code is None


async def test_recent_failures_for_the_feed(db_session_factory: Factory) -> None:
    for number in range(3):
        got = await _claim(db_session_factory, period=f"2026-11-{10 + number}")
        assert got is not None
        async with db_session_factory() as db:
            await fail(
                db, ME, got.run_id, attempt=1, code=f"c{number}", now=NOW + timedelta(hours=number)
            )
            await db.commit()
    other = await _claim(db_session_factory, user=OTHER)
    assert other is not None
    async with db_session_factory() as db:
        await fail(db, OTHER, other.run_id, attempt=1, code="autre", now=NOW)
        await db.commit()
        everything = await recent_failures(db, ME, None, 10)
        since = await recent_failures(db, ME, NOW + timedelta(hours=1), 10)
        limited = await recent_failures(db, ME, None, 1)
    assert [v.error_code for v in everything] == ["c2", "c1", "c0"]
    assert [v.error_code for v in since] == ["c2", "c1"]
    assert [v.error_code for v in limited] == ["c2"]


async def test_user_ids_lists_every_account(db_session: AsyncSession) -> None:
    db_session.add_all([User(id=ME, user_id=ME), User(id=OTHER, user_id=OTHER)])
    await db_session.commit()
    assert sorted(await user_ids(db_session)) == sorted([ME, OTHER])


async def test_ledger_never_logs_data(
    db_session_factory: Factory, caplog: pytest.LogCaptureFixture
) -> None:
    """Un « code » qui ressemble à un message (donnée) est remplacé, rangé et journalisé sous
    le code générique ; les journaux ne portent que des identifiants, nombres et codes."""
    caplog.set_level(logging.DEBUG)
    secret = "Société Fictive a refusé l'offre de Camille Exemple"
    got = await _claim(db_session_factory)
    assert got is not None
    await _fail(db_session_factory, got.run_id, code=secret)
    assert await _claim(db_session_factory, now=NOW + timedelta(minutes=1)) is not None
    async with db_session_factory() as db:
        await finish(db, ME, got.run_id, attempt=2, status="done", now=NOW, ref_id="s-1")
        await db.commit()
    assert (await _row(db_session_factory)).error_code is None
    first = (await _row(db_session_factory, period="2026-11-16")).id
    text = "\n".join(record.getMessage() for record in caplog.records)
    assert "Société" not in text and "Camille" not in text and "refusé" not in text
    assert first in text and "error" in text


async def test_stale_worker_cannot_close_a_reclaimed_attempt(db_session_factory: Factory) -> None:
    """Un ouvrier présumé mort (essai 1, `running` périmé) reprend vie après que l'essai 2 a été
    repris : sa fin tardive ne ferme ni ne fait échouer l'essai 2."""
    first = await _claim(db_session_factory)
    assert first is not None and first.attempt == 1
    second = await _claim(db_session_factory, now=NOW + timedelta(minutes=31))
    assert second == Claim(run_id=first.run_id, attempt=2)
    async with db_session_factory() as db:
        await finish(db, ME, first.run_id, attempt=1, status="done", now=NOW, ref_id="vieux")
        await fail(db, ME, first.run_id, attempt=1, code="tard", now=NOW)
        await db.commit()
    row = await _row(db_session_factory)
    assert row.status == "running" and row.attempts == 2 and row.ref_id is None
    async with db_session_factory() as db:
        await finish(db, ME, second.run_id, attempt=2, status="done", now=NOW, ref_id="s-2")
        await db.commit()
    row = await _row(db_session_factory)
    assert row.status == "done" and row.ref_id == "s-2"


async def test_concurrent_reclaim_of_a_stale_row_fences_the_old_worker(
    db_session_factory: Factory,
) -> None:
    """Cinq reprises simultanées d'un `running` périmé : un seul gagnant (essai 2) ; le retardataire
    de l'essai 1 qui termine pendant ce temps n'écrit rien."""
    first = await _claim(db_session_factory)
    assert first is not None
    later = NOW + timedelta(minutes=31)

    async def stale_finish() -> None:
        async with db_session_factory() as db:
            await finish(db, ME, first.run_id, attempt=1, status="done", now=later)
            await db.commit()

    results = await asyncio.gather(
        stale_finish(), *[_claim(db_session_factory, now=later) for _ in range(5)]
    )
    claims = [r for r in results[1:] if r is not None]
    row = await _row(db_session_factory)
    # Selon l'ordre, le retardataire ferme l'essai 1 avant toute reprise (alors `done`, jamais
    # repris) ou arrive trop tard et n'écrit rien : jamais une reprise perdue ni deux gagnants.
    if row.status == "done":
        assert claims == [] and row.attempts == 1
    else:
        assert len(claims) == 1 and claims[0].attempt == 2
        assert row.status == "running" and row.attempts == 2 and row.ref_id is None


async def test_reopen_turns_a_done_pass_back_into_a_retry(db_session_factory: Factory) -> None:
    got = await _claim(db_session_factory)
    assert got is not None
    async with db_session_factory() as db:
        await finish(db, ME, got.run_id, attempt=1, status="done", now=NOW, ref_id="s-1")
        await db.commit()
        view = await last_done(db, ME, "daily_brief")
        assert view is not None
        assert await reopen(db, ME, view, code="session_failed", now=NOW)
        assert not await reopen(db, ME, view, code="session_failed", now=NOW)  # déjà rouvert
        await db.commit()
    row = await _row(db_session_factory)
    assert row.status == "failed" and row.error_code == "session_failed"
    again = await _claim(db_session_factory, now=NOW + timedelta(minutes=1))
    assert again == Claim(run_id=got.run_id, attempt=2)
