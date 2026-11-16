"""Un passage rouvert est daté de sa réouverture (D173)."""

from datetime import timedelta

from app.features.ledger.service.ledger import finish, last_done, recent_failures, reopen
from tests.features.ledger.test_ledger import ME, NOW, Factory, _claim


async def test_reopen_dates_the_failure_at_the_reopening(db_session_factory: Factory) -> None:
    """Un passage rouvert des jours après son lancement est daté de la réouverture : le fil
    d'activité le montre en haut, pas dans le passé (D173)."""
    got = await _claim(db_session_factory)
    assert got is not None
    late = NOW + timedelta(days=3)
    async with db_session_factory() as db:
        await finish(db, ME, got.run_id, attempt=1, status="done", now=NOW, ref_id="s-1")
        await db.commit()
        view = await last_done(db, ME, "daily_brief")
        assert view is not None
        assert await reopen(db, ME, view, code="session_failed", now=late)
        await db.commit()
        [failed] = await recent_failures(db, ME, NOW + timedelta(days=2), None, 10)
    assert failed.finished_at == late and failed.error_code == "session_failed"
