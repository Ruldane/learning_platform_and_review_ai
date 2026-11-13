"""Courbe de progression (D106, D107) : relevés hebdomadaires lus, semaine en cours calculée en
direct, semaines dans le fuseau de January."""

from datetime import UTC, date, datetime
from typing import Any

from app.features.settings.service import SettingsService
from app.features.skills.history import skill_history
from tests.features.skills.support import NOW, WEEK, Factory, add_skill, add_snapshot

ME, OTHER = "moi", "autre"


def _points(out: Any) -> list[tuple[date, tuple[int, int, int, int], int]]:
    return [
        (
            p.week_start,
            (p.counts.declare, p.counts.en_cours, p.counts.valide, p.counts.prouve),
            p.score,
        )
        for p in out.points
    ]


async def test_history_includes_live_current_week(db_session_factory: Factory) -> None:
    """Le relevé de la semaine W (écrit au début de W) est l'état de fin de W − 1 : tracé sous
    W − 1 (revue finale 5, relecture 5.10 m7)."""
    a = await add_skill(db_session_factory, ME, "Pandas", None, "valide")
    b = await add_skill(db_session_factory, ME, "SQL", None, "prouve")
    await add_skill(db_session_factory, ME, "Git")  # sans niveau : hors de la courbe
    await add_snapshot(db_session_factory, ME, date(2026, 8, 3), {a: "declare"})  # trop ancien
    await add_snapshot(db_session_factory, ME, date(2026, 11, 2), {a: "declare", b: "en_cours"})
    await add_snapshot(db_session_factory, ME, date(2026, 11, 9), {a: "en_cours", b: "valide"})
    await add_snapshot(db_session_factory, ME, WEEK, {a: "declare"})  # fin de la semaine du 9/11
    await add_snapshot(db_session_factory, OTHER, date(2026, 11, 9), {"x": "prouve"})
    async with db_session_factory() as db:
        twelve = await skill_history(db, ME, 12, NOW)
        two = await skill_history(db, ME, 2, NOW)
        one = await skill_history(db, ME, 1, NOW)
    assert _points(twelve) == [
        (date(2026, 10, 26), (1, 1, 0, 0), 38),  # relevé du 2/11 : (25 + 50) / 2 = 37,5 → 38
        (date(2026, 11, 2), (0, 1, 1, 0), 63),  # relevé du 9/11 : 62,5 → 63
        (date(2026, 11, 9), (1, 0, 0, 0), 25),  # relevé du 16/11
        (WEEK, (0, 0, 1, 1), 88),  # en direct : (75 + 100) / 2 = 87,5 → 88
    ]
    assert _points(two) == _points(twelve)[2:]
    assert _points(one) == [(WEEK, (0, 0, 1, 1), 88)]


async def test_history_without_levels_has_one_empty_point(db_session_factory: Factory) -> None:
    async with db_session_factory() as db:
        out = await skill_history(db, ME, 12, NOW)
    assert _points(out) == [(WEEK, (0, 0, 0, 0), 0)]


async def test_history_week_follows_user_timezone(db_session_factory: Factory) -> None:
    """Lundi 16/11 à 3 h UTC : encore dimanche 15/11 à New York, donc semaine du 9/11."""
    async with db_session_factory() as db:
        service = SettingsService(db, ME)
        current = await service.get()
        await service.replace(current.model_copy(update={"timezone": "America/New_York"}))
        await db.commit()
    moment = datetime(2026, 11, 16, 3, 0, tzinfo=UTC)
    async with db_session_factory() as db:
        out = await skill_history(db, ME, 1, moment)
    assert [p.week_start for p in out.points] == [date(2026, 11, 9)]
