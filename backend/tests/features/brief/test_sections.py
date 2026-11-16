"""Rubriques du brief calculées par le code (P9, P11, D162) : bloc, révisions, relances, offres
nouvelles depuis le brief précédent, avancement de la semaine du programme validé. Horloge figée
au mardi 17 novembre 2026, 11 h à Paris."""

import gc
import warnings
from datetime import timedelta
from typing import Any, cast

import httpx
from sqlalchemy import update

from app.db.models.daily import Brief
from app.db.models.postings import JobPosting
from app.db.models.program import Task
from app.db.models.study import StudySession
from app.features.brief.service.sections import _isolated
from app.features.radar.service.views import offers_since
from tests.features.brief.conftest import NOW, TODAY, Env
from tests.features.brief.support import (
    add_cards,
    add_run,
    add_user,
    applied,
    posting,
    sections_for,
)
from tests.features.study.conftest import seed


async def test_empty_account_has_only_empty_rubrics(env: Env) -> None:
    sections = await sections_for(env)
    assert sections == {
        "block": None,
        "reviews": {"queue": 0, "remaining": 0},
        "reminders": {"due": 0, "items": []},
        "offers": {"run_id": None, "items": []},
        "week": None,
    }


async def test_block_is_the_due_tasks_of_the_first_module(env: Env) -> None:
    seeded = await seed(env.app)
    env.at(NOW)
    block = (await sections_for(env))["block"]
    assert block == {
        "module_title": "Module Bases",
        "lesson_id": seeded.lessons[0],
        "lesson_title": "Leçon Module Bases",
        "minutes": 285,
        "tasks": [
            {"title": "Lire le chapitre 1", "minutes": 120},
            {"title": "Pratiquer les bases", "minutes": 45},
            {"title": "Lire le chapitre 2", "minutes": 120},
        ],
    }


async def test_week_progress_from_validated_program(env: Env) -> None:
    seeded = await seed(env.app)
    env.at(NOW)
    async with env.rt.session_factory() as db:
        await db.execute(
            update(Task).where(Task.title == "Lire le chapitre 1").values(status="done")
        )
        for days_ago, minutes in ((0, 30), (1, 25)):  # deux jours d'étude de suite
            db.add(
                StudySession(
                    user_id=env.user_id,
                    lesson_id=seeded.lessons[0],
                    module_id=seeded.modules[0],
                    program_id=seeded.program_id,
                    mode="block",
                    status="finished",
                    minutes=minutes,
                    ended_at=NOW - timedelta(days=days_ago),
                )
            )
        await db.commit()
    week = (await sections_for(env))["week"]
    assert week == {
        "planned_minutes": 665,  # cinq lectures de 120, pratique 45, quiz 20 : cette semaine
        "done_minutes": 120,
        "tasks_done": 1,
        "tasks_total": 7,
        "study_minutes": 55,
        "streak_days": 2,
        "best_quiz": None,
    }


async def test_draft_program_gives_no_week(env: Env) -> None:
    await seed(env.app, validated=False)
    env.at(NOW)
    assert (await sections_for(env))["week"] is None


async def test_reviews_count_the_queue_and_the_rest(env: Env) -> None:
    await add_cards(env, 40, due=TODAY - timedelta(days=1))
    await add_cards(env, 3, due=TODAY + timedelta(days=1))  # pas encore dues
    assert (await sections_for(env))["reviews"] == {"queue": 30, "remaining": 10}


async def test_due_reminder_listed(client: httpx.AsyncClient, env: Env) -> None:
    application_id = await applied(client, 8)  # postulée il y a 8 jours : la relance de 7 jours
    reminders = (await sections_for(env))["reminders"]
    assert reminders["due"] == 1
    [item] = reminders["items"]
    assert item["application_id"] == application_id and item["kind"] == "linkedin_7"
    assert (item["company"], item["title"]) == ("Société Fictive", "Développeuse IA")
    assert item["due_on"] == "2026-11-16" and item["reminder_id"]


async def test_reminders_list_five_items_but_count_them_all(
    client: httpx.AsyncClient, env: Env
) -> None:
    for number in range(7):
        await applied(client, 8, company=f"Société {number}")
    reminders = (await sections_for(env))["reminders"]
    assert reminders["due"] == 7 and len(reminders["items"]) == 5


async def test_first_brief_shows_the_latest_run_offers_best_first(env: Env) -> None:
    older = await add_run(env, [posting(9, 99)], finished_at=NOW - timedelta(days=9))
    run_id = await add_run(
        env,
        [posting(1, 85), posting(2, 72), posting(3, 60), posting(4, None), posting(5, 70)],
    )
    offers = (await sections_for(env))["offers"]
    assert older != run_id and offers["run_id"] == run_id
    assert [(o["title"], o["score"]) for o in offers["items"]] == [
        ("Poste 1", 85),
        ("Poste 2", 72),
        ("Poste 5", 70),
    ]  # 60 est sous le seuil, une offre sans score est ignorée, le relevé plus ancien aussi
    assert offers["items"][0]["url"] == "https://jobs.example.org/offres/1"
    assert offers["items"][0]["company"] == "Société Fictive"


async def test_offers_new_since_last_brief_only(env: Env) -> None:
    await add_run(env, [posting(1, 90), posting(2, 80)], finished_at=NOW - timedelta(days=2))
    async with env.rt.session_factory() as db:
        db.add(  # le brief d'hier : créé après le premier relevé, il a montré l'offre 1
            Brief(
                user_id=env.user_id,
                day=TODAY - timedelta(days=1),
                origin="schedule",
                sections={},
                offer_keys=["https://jobs.example.org/offres/1"],
                created_at=NOW - timedelta(days=1),
            )
        )
        await db.commit()
    assert (await sections_for(env))["offers"] == {"run_id": None, "items": []}  # rien de neuf
    fresh = await add_run(
        env,
        [posting(1, 95), posting(3, 75), posting(2, 40)],  # l'offre 1 est déjà montrée
        finished_at=NOW - timedelta(hours=1),
    )
    offers = (await sections_for(env))["offers"]
    assert offers["run_id"] == fresh
    assert [o["title"] for o in offers["items"]] == ["Poste 3"]  # 1 déjà montrée, 2 sous le seuil


async def test_offers_shown_in_the_last_seven_briefs_are_not_repeated(env: Env) -> None:
    run_id = await add_run(env, [posting(n, 90 - n) for n in range(1, 10)], finished_at=NOW)
    async with env.rt.session_factory() as db:
        for days in range(1, 9):  # huit briefs ; l'offre `n` a été montrée le jour -n
            db.add(
                Brief(
                    user_id=env.user_id,
                    day=TODAY - timedelta(days=days),
                    origin="opening",
                    sections={},
                    offer_keys=[f"https://jobs.example.org/offres/{days}"],
                    created_at=NOW - timedelta(days=days, hours=3),
                )
            )
        await db.commit()
    offers = (await sections_for(env))["offers"]
    assert offers["run_id"] == run_id
    # les sept derniers briefs écartent les offres 1 à 7 ; le huitième ne compte plus
    assert [o["title"] for o in offers["items"]] == ["Poste 8", "Poste 9"]


async def test_known_postings_and_applications_are_not_offered(
    client: httpx.AsyncClient, env: Env
) -> None:
    await add_run(env, [posting(n, 90 - n) for n in range(1, 5)])
    await applied(client, 1, url="https://jobs.example.org/offres/1")  # une fiche déjà saisie
    async with env.rt.session_factory() as db:
        db.add(  # une offre déjà analysée
            JobPosting(
                user_id=env.user_id,
                url="https://jobs.example.org/offres/2",
                url_norm="https://jobs.example.org/offres/2",
                text="Offre fictive.",
                text_hash="h",
                source="url",
            )
        )
        await db.commit()
    offers = (await sections_for(env))["offers"]
    assert [o["title"] for o in offers["items"]] == ["Poste 3", "Poste 4"]


async def test_at_most_five_offers(env: Env) -> None:
    await add_run(env, [posting(n, 70 + n) for n in range(1, 9)])
    items = (await sections_for(env))["offers"]["items"]
    assert [o["score"] for o in items] == [78, 77, 76, 75, 74]


async def test_failed_runs_are_not_offered(env: Env) -> None:
    await add_run(env, [posting(1, 90)], status="failed")
    assert (await sections_for(env))["offers"]["items"] == []


async def test_sections_of_another_user_are_invisible(env: Env) -> None:
    await add_user(env, "autre")
    await add_run(env, [posting(1, 90)], user="autre")
    await add_cards(env, 4, user="autre")
    mine = await sections_for(env)
    assert mine["offers"]["items"] == [] and mine["reviews"] == {"queue": 0, "remaining": 0}
    theirs = await sections_for(env, "autre")
    assert len(theirs["offers"]["items"]) == 1 and theirs["reviews"]["queue"] == 4


async def test_offers_since_reads_only_scored_analyzed_entries_of_done_runs(env: Env) -> None:
    await add_run(
        env,
        [
            posting(1, 80),
            posting(2, None),  # pas de score
            posting(3, 70, read="not_posting"),  # pas une offre
            posting(4, 71, key=""),  # sans lien normalisé
        ],
    )
    async with env.rt.session_factory() as db:
        found = await offers_since(db, env.user_id, None)
        none_after = await offers_since(db, env.user_id, NOW)
    assert [entry["score"] for entry in found] == [80]
    assert set(found[0]) == {"run_id", "url_key", "url", "title", "company", "score"}
    assert none_after == []


class _BrokenDb:
    """Une session dont le savepoint ne s'ouvre pas : la fabrique ne doit jamais être appelée."""

    def begin_nested(self) -> Any:
        raise RuntimeError("savepoint impossible")


async def test_a_failing_source_leaves_no_unawaited_coroutine_and_a_fresh_empty(
    env: Env,
) -> None:
    built: list[str] = []

    async def source() -> Any:
        built.append("called")
        raise RuntimeError("source en panne")

    failed: list[str] = []
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        broken = await _isolated(cast(Any, _BrokenDb()), "reminders", source, failed)
        async with env.rt.session_factory() as db:
            first = await _isolated(db, "reminders", source, failed)
        gc.collect()
    assert built == ["called"]  # jamais appelée quand le savepoint ne s'ouvre pas
    assert failed == ["reminders", "reminders"]
    assert broken == first == {"due": 0, "items": []}
    first["items"].append("x")  # une valeur neuve : rien ne fuit vers l'appel suivant
    assert (await _isolated(cast(Any, _BrokenDb()), "reminders", source, failed))["items"] == []
