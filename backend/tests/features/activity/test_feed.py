"""Le fil d'activité (P15, D163) : la fusion des sources par instant, `after` et `before`, les
écritures de l'utilisatrice exclues, un échec de passage sans texte d'erreur, le plafond de 50,
l'isolation par utilisatrice et des journaux sans donnée."""

import logging

import pytest

from app.features.activity.service.sources import ACTIVITY_SOURCES
from tests.features.activity.support import (
    OTHER,
    Env,
    add_brief,
    add_job,
    add_run,
    add_user,
    add_write,
    hours,
    minutes,
    set_lesson,
)
from tests.features.activity.support import page as _page
from tests.features.study.conftest import seed


async def _everything(env: Env) -> tuple[str, str]:
    """Une ligne par source, dans un ordre qui n'est pas celui du registre. Rend les deux leçons."""
    seeded = await seed(env.app)
    ready, failed = seeded.lessons
    await set_lesson(env, ready, "ready", hours(1))
    await add_job(env, hours(2), name="market_radar", period="2026-W47")
    await add_write(env, hours(3), author="analyst", reason="Le niveau a changé.")
    await add_run(env, hours(4))
    await add_brief(env, hours(5))
    await set_lesson(env, failed, "failed", hours(6))
    return ready, failed


async def test_feed_merges_sources_by_time(env: Env) -> None:
    ready, failed = await _everything(env)
    page = await _page(env)
    assert [item.kind for item in page.items] == [
        "lesson",
        "brief",
        "radar",
        "memory",
        "job_failed",
        "lesson",
    ]
    assert [item.at for item in page.items] == [hours(h) for h in (6, 5, 4, 3, 2, 1)]
    assert page.latest_at == hours(6)
    by_kind = {(item.kind, item.at): item for item in page.items}
    lesson_fail = by_kind["lesson", hours(6)]
    assert lesson_fail.title == "Leçon en échec : Leçon Module Projet"
    assert lesson_fail.link == f"/apprendre/lecons/{failed}"
    assert lesson_fail.id == f"lesson:{failed}:failed"
    assert by_kind["lesson", hours(1)].title == "Leçon prête : Leçon Module Bases"
    assert by_kind["lesson", hours(1)].id == f"lesson:{ready}:ready"
    radar = by_kind["radar", hours(4)]
    assert radar.title == "Relevé du radar : 47 offres lues, 6 bloquées"
    assert radar.link == f"/carriere/radar/{radar.id.split(':')[1]}"
    brief = by_kind["brief", hours(5)]
    assert brief.title == "Brief du jour prêt" and brief.link == "/"
    memory = by_kind["memory", hours(3)]
    assert memory.title == "L'Analyste a écrit en mémoire : Élément secret"
    assert memory.detail == "Le niveau a changé."
    job = by_kind["job_failed", hours(2)]
    assert job.title == (
        "Un passage planifié a échoué (radar du marché) : nouvel essai au prochain passage."
    )
    assert len({item.id for item in page.items}) == 6
    assert len(ACTIVITY_SOURCES) == 6  # leçons, radar, brief, projets, mémoire, passages


async def test_after_returns_only_newer(env: Env) -> None:
    await _everything(env)
    page = await _page(env, after=hours(4))
    assert [item.kind for item in page.items] == ["lesson", "brief"]  # strictement après 4 h
    assert page.latest_at == hours(6)
    empty = await _page(env, after=hours(6))
    assert empty.items == [] and empty.latest_at is None


async def test_before_pages_older(env: Env) -> None:
    await _everything(env)
    first = await _page(env, limit=2)
    assert [item.at for item in first.items] == [hours(6), hours(5)]
    last = first.items[-1]
    second = await _page(env, before=last.at, before_id=last.id, limit=2)
    assert [item.at for item in second.items] == [hours(4), hours(3)]
    last = second.items[-1]
    third = await _page(env, before=last.at, before_id=last.id, limit=2)
    assert [item.at for item in third.items] == [hours(2), hours(1)]
    ids = [item.id for page in (first, second, third) for item in page.items]
    assert len(set(ids)) == 6
    assert (await _page(env, before=hours(1))).items == []
    window = await _page(env, after=hours(2), before=hours(5))
    assert [item.at for item in window.items] == [hours(4), hours(3)]


async def test_user_writes_excluded(env: Env) -> None:
    await add_write(env, hours(1), author="user", title="Écrit par January")
    await add_write(env, hours(2), author="scribe", action="delete", title="Supprimé")
    await add_write(env, hours(3), author="mystery_agent", title="Écrit par un agent", reason=None)
    page = await _page(env)
    assert [item.title for item in page.items] == [
        "Un agent a écrit en mémoire : Écrit par un agent"
    ]
    assert page.items[0].detail is None


async def test_job_failure_item_has_no_error_text(env: Env) -> None:
    await add_job(env, hours(1), code="secret_error_code")
    await add_job(env, hours(2), name="inconnue", period="p2")
    await add_job(env, hours(3), status="done", code=None, period="p3")  # un succès n'y est pas
    page = await _page(env)
    assert len(page.items) == 2
    dumped = page.model_dump_json()
    assert "secret_error_code" not in dumped and "error" not in dumped.replace("job_failed", "")
    assert all(item.detail is None and item.link is None for item in page.items)
    assert page.items[0].title == (
        "Un passage planifié a échoué (tâche de fond) : nouvel essai au prochain passage."
    )
    assert page.items[1].title.startswith("Un passage planifié a échoué (brief du matin)")


async def test_limit_capped_at_50(env: Env) -> None:
    for number in range(60):
        await add_write(env, minutes(number), title=f"Élément {number}")
    assert len((await _page(env, limit=100)).items) == 50
    assert len((await _page(env, limit=30)).items) == 30
    assert len((await _page(env, limit=0)).items) == 1  # plancher : jamais une page vide à tort
    page = await _page(env, limit=100)
    assert page.items[0].title.endswith("Élément 59")


async def test_activity_isolated_by_user(env: Env) -> None:
    await _everything(env)
    await add_user(env)
    assert (await _page(env, user=OTHER)).items == []
    await add_run(env, hours(7), user=OTHER, read_count=3, blocked_count=0)
    await add_brief(env, hours(8), user=OTHER)
    await add_write(env, hours(9), user=OTHER, title="Pour l'autre")
    await add_job(env, hours(10), user=OTHER, period="autre")
    other = await _page(env, user=OTHER)
    assert len(other.items) == 4
    mine = await _page(env)
    assert len(mine.items) == 6 and not {i.id for i in mine.items} & {i.id for i in other.items}
    assert all("Pour l'autre" not in item.title for item in mine.items)


async def test_activity_never_logged(env: Env, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    await _everything(env)
    await add_job(env, hours(7), code="secret_error_code", period="p9")
    page = await _page(env)
    assert page.items
    text = "\n".join(record.getMessage() for record in caplog.records)
    for secret in (
        "Élément secret",
        "Raison secrète",
        "Le niveau a changé",
        "Leçon Module",
        "Poste secret",
        "Zone secrète",
        "secret_error_code",
    ):
        assert secret not in text, secret
