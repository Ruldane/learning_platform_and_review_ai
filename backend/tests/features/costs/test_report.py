"""Le rapport lu en base : la fenêtre en jours locaux, les prix de l'appel, l'isolation."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.accounts import UserSettingsRow
from app.db.models.agents import LlmCall
from app.features.costs.repository import LlmCallRepository
from app.features.costs.service.report import costs_report

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


def add(db: AsyncSession, user_id: str, at: datetime, **over: object) -> None:
    fields: dict[str, object] = {
        "user_id": user_id,
        "created_at": at,
        "graph": "capture",
        "agent": "extractor",
        "provider": "glm",
        "model": "glm-5.3-flash",
        "tokens_in": 100,
        "tokens_out": 50,
        "cost_usd": 0.25,
    }
    db.add(LlmCall(**{**fields, **over}))


async def test_report_reads_own_calls_in_window(db_session: AsyncSession) -> None:
    add(db_session, "u1", NOW - timedelta(days=2))
    add(db_session, "u1", NOW - timedelta(days=20), graph=None)
    add(db_session, "u1", NOW - timedelta(days=40))  # hors des 30 jours
    add(db_session, "u2", NOW - timedelta(days=2), cost_usd=9.0)  # autre utilisatrice
    await db_session.flush()
    report = await costs_report(db_session, "u1", 30, now=NOW)
    assert report.days == 30 and str(report.until) == "2026-11-16"
    assert report.total.calls == 2 and report.total.cost_usd == 0.5
    assert [r.key for r in report.by_feature] == ["", "capture"]


async def test_window_starts_at_local_midnight(db_session: AsyncSession) -> None:
    # Europe/Paris par défaut (UTC+1 en novembre) : le 10/11 local commence le 9/11 à 23 h UTC.
    add(db_session, "u1", datetime(2026, 11, 9, 22, 59, tzinfo=UTC))  # 9/11 23 h 59 local : dehors
    add(db_session, "u1", datetime(2026, 11, 9, 23, 0, tzinfo=UTC))  # 10/11 00 h local : dedans
    await db_session.flush()
    report = await costs_report(db_session, "u1", 7, now=NOW)
    assert report.total.calls == 1 and report.by_day[0].key == "2026-11-10"
    assert report.by_day[0].calls == 1


async def test_report_uses_the_user_zone(db_session: AsyncSession) -> None:
    db_session.add(UserSettingsRow(user_id="u1", data={"timezone": "Pacific/Auckland"}))
    # 16/11 12 h UTC = 17/11 01 h à Auckland (UTC+13) : « aujourd'hui » est le 17.
    add(db_session, "u1", NOW)
    await db_session.flush()
    report = await costs_report(db_session, "u1", 7, now=NOW)
    assert str(report.until) == "2026-11-17" and report.by_day[-1].calls == 1


async def test_repository_since_is_user_scoped_and_ordered(db_session: AsyncSession) -> None:
    add(db_session, "u1", NOW - timedelta(hours=1))
    add(db_session, "u1", NOW - timedelta(hours=3))
    add(db_session, "u1", NOW - timedelta(days=5))
    add(db_session, "u2", NOW - timedelta(hours=2))
    await db_session.flush()
    rows = await LlmCallRepository(db_session, "u1").since(NOW - timedelta(days=1))
    assert [r.created_at for r in rows] == [NOW - timedelta(hours=3), NOW - timedelta(hours=1)]


async def test_repository_page_orders_newest_first_with_cursor(db_session: AsyncSession) -> None:
    for hours in (1, 2, 3, 4):
        add(db_session, "u1", NOW - timedelta(hours=hours), agent=f"a{hours}")
    add(db_session, "u2", NOW, agent="other")
    await db_session.flush()
    repo = LlmCallRepository(db_session, "u1")
    first = await repo.page(before=None, limit=2, agent=None, graph=None)
    assert [r.agent for r in first] == ["a1", "a2"]
    cursor = (first[-1].created_at, first[-1].id)
    second = await repo.page(before=cursor, limit=2, agent=None, graph=None)
    assert [r.agent for r in second] == ["a3", "a4"]
    only = await repo.page(before=None, limit=10, agent="a3", graph="capture")
    assert [r.agent for r in only] == ["a3"]
    assert await repo.page(before=None, limit=10, agent=None, graph="nope") == []


async def test_page_breaks_ties_on_id(db_session: AsyncSession) -> None:
    for call_id in ("a", "b", "c"):
        add(db_session, "u1", NOW, id=call_id)
    await db_session.flush()
    repo = LlmCallRepository(db_session, "u1")
    first = await repo.page(before=None, limit=2, agent=None, graph=None)
    assert [r.id for r in first] == ["c", "b"]
    rest = await repo.page(before=(first[-1].created_at, "b"), limit=2, agent=None, graph=None)
    assert [r.id for r in rest] == ["a"]
