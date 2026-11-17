"""Relancer les brouillons d'un projet validé qui n'en a pas (D173 n° 4, D181) :
`POST /projects/{id}/drafts` lance `project_review` en mode `drafts` (jamais d'évaluation), 409 hors
du cas (`project_not_validated`, `drafts_present`, `review_in_progress`), 404 sur le projet d'un
autre, 503 si le lancement est refusé ; le port écrit les brouillons une seule fois, sur un projet
validé qui n'en a pas. Les textes du projet ne sont jamais journalisés."""

import asyncio
import logging

import httpx
import pytest
from fastapi import FastAPI

from app.features.projects.service.store import AgentProjectStore
from tests.features.projects.support import API, Env, draft_results
from tests.sessions_support import act_as


async def validated(env: Env, **over: object) -> str:
    """Un projet validé sans brouillons : ses brouillons n'avaient pas pu s'écrire (D173 n° 4)."""
    return await env.add_project(status="validated", submissions=[env.last_submission()], **over)


async def post(client: httpx.AsyncClient, project_id: str) -> httpx.Response:
    return await client.post(f"{API}/{project_id}/drafts")


def code_of(response: httpx.Response) -> str:
    return str(response.json()["error"]["code"])


async def test_regenerate_drafts_202_then_four_drafts(env: Env, client: httpx.AsyncClient) -> None:
    pid = await validated(env)
    r = await post(client, pid)
    assert r.status_code == 202
    session_id = r.json()["session_id"]
    assert env.launcher.started == [("project_review", {"project_id": pid, "mode": "drafts"})]
    assert (await env.row(pid)).session_id == session_id
    # la session du parcours range les quatre brouillons par le port
    await AgentProjectStore(env.rt).save_drafts(env.user_id, session_id, pid, draft_results())
    await env.launcher.end(env.user_id, session_id)
    body = (await client.get(f"{API}/{pid}")).json()
    assert [d["kind"] for d in body["drafts"]] == [
        "cv_line",
        "profile_entry",
        "linkedin_post",
        "readme_plan",
    ]
    assert body["status"] == "validated"
    again = await post(client, pid)
    assert (again.status_code, code_of(again)) == (409, "drafts_present")
    assert len(env.launcher.started) == 1


async def test_regenerate_drafts_refused_when_present(env: Env, client: httpx.AsyncClient) -> None:
    pid = await validated(
        env, drafts={"cv_line": {"status": "ready", "content": "x", "flags": [], "edited": False}}
    )
    r = await post(client, pid)
    assert (r.status_code, code_of(r)) == (409, "drafts_present")
    assert not env.launcher.started


@pytest.mark.parametrize("status", ["todo", "to_redo", "brief_pending", "brief_failed"])
async def test_regenerate_drafts_refused_not_validated(
    env: Env, client: httpx.AsyncClient, status: str
) -> None:
    pid = await env.add_project(status=status, brief=status in ("todo", "to_redo"))
    r = await post(client, pid)
    assert (r.status_code, code_of(r)) == (409, "project_not_validated")
    assert not env.launcher.started and (await env.row(pid)).status == status


async def test_regenerate_drafts_refused_while_reviewing(
    env: Env, client: httpx.AsyncClient
) -> None:
    pid = await env.add_project()
    submitted = await client.post(f"{API}/{pid}/submit", data={"description": "Mon travail."})
    session_id = submitted.json()["session_id"]
    r = await post(client, pid)
    assert (r.status_code, code_of(r)) == (409, "review_in_progress")
    assert r.json()["error"]["details"] == {"session_id": session_id}
    assert "évaluation" in r.json()["error"]["message"]  # le rendu en cours garde son message
    assert len(env.launcher.started) == 1  # seul le rendu a lancé un parcours


async def test_regenerate_drafts_twice_is_review_in_progress(
    env: Env, client: httpx.AsyncClient
) -> None:
    pid = await validated(env)
    session_id = (await post(client, pid)).json()["session_id"]
    again = await post(client, pid)
    assert (again.status_code, code_of(again)) == (409, "review_in_progress")
    assert again.json()["error"]["details"] == {"session_id": session_id}
    assert again.json()["error"]["message"] == "Les brouillons s'écrivent déjà."
    assert len(env.launcher.started) == 1
    await env.launcher.end(env.user_id, session_id, "failed")  # la session est close : on relance
    assert (await post(client, pid)).status_code == 202


async def test_two_simultaneous_regenerations_start_one_session(
    env: Env, client: httpx.AsyncClient
) -> None:
    pid = await validated(env)
    first, second = await asyncio.gather(post(client, pid), post(client, pid))
    assert sorted((first.status_code, second.status_code)) == [202, 409]
    refused = first if first.status_code == 409 else second
    started = first if first.status_code == 202 else second
    assert code_of(refused) == "review_in_progress"
    assert refused.json()["error"]["details"] == {"session_id": started.json()["session_id"]}
    assert len(env.launcher.started) == 1


async def test_validated_project_shows_the_session_of_its_drafts_while_it_runs(
    env: Env, client: httpx.AsyncClient
) -> None:
    """Après un rechargement, le front retrouve la session des brouillons (schéma inchangé)."""
    pid = await validated(env)
    assert (await client.get(f"{API}/{pid}")).json()["session_id"] is None
    session_id = (await post(client, pid)).json()["session_id"]
    assert (await client.get(f"{API}/{pid}")).json()["session_id"] == session_id
    [listed] = [p for p in (await client.get(API)).json() if p["id"] == pid]
    assert listed["session_id"] == session_id
    await env.launcher.end(env.user_id, session_id)  # la session est close : plus rien à suivre
    assert (await client.get(f"{API}/{pid}")).json()["session_id"] is None
    [listed] = [p for p in (await client.get(API)).json() if p["id"] == pid]
    assert listed["session_id"] is None


async def test_profile_entry_answer_shows_the_session_of_its_drafts(
    env: Env, client: httpx.AsyncClient
) -> None:
    """La réponse du clic « ajouter au profil » rend le projet comme `GET /projects/{id}` (M4)."""
    await env.add_profile(3)
    pid = await validated(env)
    session_id = (await post(client, pid)).json()["session_id"]
    entry = {"name": "Suivi de lecture", "description": "Une API de suivi.", "achievements": []}
    r = await client.post(f"{API}/{pid}/profile-entry", json=entry)
    assert r.status_code == 200, r.text
    assert r.json()["session_id"] == session_id
    assert (await client.get(f"{API}/{pid}")).json()["session_id"] == session_id


async def test_regenerate_drafts_of_another_users_project_is_404(
    env: Env, app: FastAPI, client: httpx.AsyncClient
) -> None:
    pid = await validated(env)
    missing = await post(client, "00000000-0000-4000-8000-000000000000")
    assert (missing.status_code, code_of(missing)) == (404, "project_not_found")
    act_as(app, "autre-utilisatrice")
    try:
        stranger = await post(client, pid)
    finally:
        act_as(app, env.user_id)
    assert (stranger.status_code, code_of(stranger)) == (404, "project_not_found")
    assert stranger.json() == missing.json() and not env.launcher.started


async def test_regenerate_drafts_unavailable_engine_is_503(
    env: Env, client: httpx.AsyncClient
) -> None:
    pid = await validated(env)
    env.launcher.refuse = True
    r = await post(client, pid)
    assert (r.status_code, code_of(r)) == (503, "drafts_unavailable")
    row = await env.row(pid)
    assert row.status == "validated" and row.session_id is None and row.drafts == {}
    env.launcher.refuse = False
    assert (await post(client, pid)).status_code == 202


# -- le port : `save_drafts` ------------------------------------------------------------------


async def test_save_drafts_first_write_wins(env: Env) -> None:
    pid = await validated(env)
    store = AgentProjectStore(env.rt)
    assert await store.save_drafts(env.user_id, "s1", pid, draft_results()) is True
    first = (await env.row(pid)).drafts
    assert set(first) == {"cv_line", "profile_entry", "linkedin_post", "readme_plan"}
    assert all(item["edited"] is False and item["status"] == "ready" for item in first.values())
    ignored = await store.save_drafts(env.user_id, "s2", pid, draft_results(to_check=["cv_line"]))
    assert (
        ignored is False and (await env.row(pid)).drafts == first
    )  # rejeu ou autre session : rien de plus


async def test_save_drafts_does_nothing_without_drafts_or_off_a_validated_project(
    env: Env,
) -> None:
    store = AgentProjectStore(env.rt)
    pid = await validated(env)
    # « brouillons indisponibles » de nouveau
    assert await store.save_drafts(env.user_id, "s1", pid, []) is False
    assert (await env.row(pid)).drafts == {}
    todo = await env.add_project(1, status="to_redo")
    assert await store.save_drafts(env.user_id, "s1", todo, draft_results()) is False
    row = await env.row(todo)
    assert row.drafts == {} and row.status == "to_redo"


async def test_regenerate_drafts_never_logged(
    env: Env, client: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    pid = await validated(env, title="SECRET-TITRE")
    session_id = (await post(client, pid)).json()["session_id"]
    await post(client, pid)  # le refus
    await AgentProjectStore(env.rt).save_drafts(
        env.user_id, session_id, pid, draft_results(to_check=["cv_line"])
    )
    logged = "\n".join(r.getMessage() for r in caplog.records if r.name.startswith("app"))
    assert pid in logged and session_id in logged
    for secret in ("SECRET-TITRE", "Construit une API", "kubernetes", "FastAPI"):
        assert secret not in logged
