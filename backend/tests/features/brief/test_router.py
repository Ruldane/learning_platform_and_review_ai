"""`GET /brief/today` (14.2, D162) : la forme rendue, les rubriques, l'origine, le statut du conseil
(un seul état change encore, `pending` ; `failed` et `unavailable` sont définitifs) et la session
morte."""

from datetime import timedelta

import httpx
from fastapi import FastAPI
from sqlalchemy import update

from app.agents.tools.brief_schema import ResourceView
from app.db.models.daily import Brief
from app.features.brief.service.store import AgentBriefStore
from tests.features.brief.conftest import NOW, Env
from tests.features.brief.support import (
    add_cards,
    add_run,
    applied,
    brief_sessions,
    briefs,
    get_today,
    posting,
)
from tests.features.study.conftest import seed

RESOURCE = ResourceView(
    title="Guide fictif",
    url="https://docs.example.org/guide",
    domain="docs.example.org",
    published="2026-11-10",
    why="Un guide récent.",
)
ADVICE = ["Commence par ton bloc du jour.", "Puis passe tes fiches en revue."]


async def test_get_today_creates_with_all_rubrics(client: httpx.AsyncClient, env: Env) -> None:
    await seed(env.app)
    env.at(NOW)
    await add_cards(env, 2)
    await applied(client, 8)
    await add_run(env, [posting(1, 88)])
    b = await get_today(client)
    assert set(b) >= {"block", "reviews", "reminders", "offers", "week", "resource", "advice"}
    assert b["origin"] == "opening" and b["day"] == "2026-11-17" and b["generated_at"]
    assert b["block"]["lesson_title"] == "Leçon Module Bases" and b["block"]["minutes"] == 285
    assert b["reviews"] == {"queue": 2, "remaining": 0}
    assert b["reminders"]["due"] == 1 and b["reminders"]["items"][0]["kind"] == "linkedin_7"
    assert b["offers"]["items"] == [
        {
            "url": "https://jobs.example.org/offres/1",
            "title": "Poste 1",
            "company": "Société Fictive",
            "score": 88,
        }
    ]
    assert b["week"]["tasks_total"] == 7 and b["week"]["streak_days"] == 0
    assert b["resource"] is None and b["advice"] is None  # arrivent ensuite
    assert b["advice_status"] == "pending" and b["session_id"]


async def test_internal_details_are_not_in_the_contract(
    client: httpx.AsyncClient, env: Env
) -> None:
    await seed(env.app)
    env.at(NOW)
    await add_run(env, [posting(1, 88)])
    body = await get_today(client)
    assert "key" not in body["offers"]["items"][0] and "best_quiz" not in body["week"]


async def test_the_opening_never_waits_for_an_agent(client: httpx.AsyncClient, env: Env) -> None:
    body = await get_today(client)  # le lanceur factice n'exécute aucun parcours
    assert body["advice_status"] == "pending" and body["advice"] is None
    assert await brief_sessions(env) == 1


async def test_resource_and_advice_appear_once_stored(client: httpx.AsyncClient, env: Env) -> None:
    body = await get_today(client)
    store = AgentBriefStore(env.rt)
    sid = body["session_id"]
    await store.save_resource(env.user_id, sid, body["id"], RESOURCE)
    await store.save_advice(env.user_id, sid, body["id"], ADVICE)
    await env.launcher.end(env.user_id, sid, "completed")
    done = await get_today(client)
    assert done["resource"] == {
        "title": "Guide fictif",
        "url": "https://docs.example.org/guide",
        "domain": "docs.example.org",
        "published": "2026-11-10",
        "why": "Un guide récent.",
    }
    assert done["advice"] == ADVICE and done["advice_status"] == "ready"


async def test_empty_resource_is_null_and_the_advice_still_comes(
    client: httpx.AsyncClient, env: Env
) -> None:
    body = await get_today(client)
    store = AgentBriefStore(env.rt)
    await store.save_resource(env.user_id, body["session_id"], body["id"], None)
    await store.save_advice(env.user_id, body["session_id"], body["id"], ADVICE)
    done = await get_today(client)
    assert done["resource"] is None and done["advice"] == ADVICE


async def test_dead_session_marks_advice_failed(client: httpx.AsyncClient, env: Env) -> None:
    body = await get_today(client)
    assert (await get_today(client))["advice_status"] == "pending"  # la session vit
    await env.launcher.end(env.user_id, body["session_id"], "failed")
    failed = await get_today(client)
    assert failed["advice_status"] == "failed" and failed["advice"] is None
    assert failed["block"] is None and failed["reviews"] == {"queue": 0, "remaining": 0}
    assert (await briefs(env))[0].advice_status == "failed"  # écrit, et définitif


async def test_a_closed_session_without_advice_is_failed_whatever_its_status(
    client: httpx.AsyncClient, env: Env
) -> None:
    body = await get_today(client)
    await env.launcher.end(env.user_id, body["session_id"], "completed")
    assert (await get_today(client))["advice_status"] == "failed"


async def test_a_stored_advice_is_not_downgraded_when_the_session_closes(
    client: httpx.AsyncClient, env: Env
) -> None:
    body = await get_today(client)
    await AgentBriefStore(env.rt).save_advice(env.user_id, body["session_id"], body["id"], ADVICE)
    await env.launcher.end(env.user_id, body["session_id"], "cancelled")
    again = await get_today(client)
    assert again["advice_status"] == "ready" and again["advice"] == ADVICE


async def test_failed_advice_is_final_for_the_day_in_the_api(
    client: httpx.AsyncClient, env: Env
) -> None:
    body = await get_today(client)
    store = AgentBriefStore(env.rt)
    await store.save_advice(env.user_id, body["session_id"], body["id"], None)
    await store.save_advice(env.user_id, body["session_id"], body["id"], ADVICE)  # ignoré
    final = await get_today(client)
    assert final["advice_status"] == "failed" and final["advice"] is None
    assert len(env.launcher.started) == 1  # aucune relance


async def test_the_contract_says_which_statuses_are_final(app: FastAPI) -> None:
    schema = app.openapi()["components"]["schemas"]["BriefOut"]
    status = schema["properties"]["advice_status"]
    assert "définitifs" in status["description"] and "failed" in status["description"]
    assert "unavailable" in schema["description"] and "Réessayer" in schema["description"]
    assert set(schema["properties"]) >= {
        "id",
        "day",
        "origin",
        "generated_at",
        "block",
        "reviews",
        "reminders",
        "offers",
        "week",
        "resource",
        "advice",
        "advice_status",
        "session_id",
    }


async def test_a_launch_interrupted_before_the_session_was_recorded_ends_failed(
    client: httpx.AsyncClient, env: Env
) -> None:
    body = await get_today(client)
    async with env.rt.session_factory() as db:  # le processus s'est arrêté avant `set_session`
        await db.execute(update(Brief).where(Brief.id == body["id"]).values(session_id=None))
        await db.commit()
    assert (await get_today(client))["advice_status"] == "pending"  # un instant de grâce
    env.at(NOW + timedelta(minutes=6))
    assert (await get_today(client))["advice_status"] == "failed"
