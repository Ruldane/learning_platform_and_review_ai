"""Isolation entre utilisatrices (D166) : le projet, ses captures, ses brouillons, son entrée au
profil, son rendu et son énoncé d'une utilisatrice sont introuvables (404 `project_not_found`, le
même qu'un projet inconnu) pour une autre, alors que le projet existe bel et bien."""

import httpx
import pytest
from fastapi import FastAPI

from app.features.projects.service.store import AgentProjectStore
from tests.features.projects.support import API, PNG, Env, outcome, shots, submit
from tests.sessions_support import act_as

STRANGER = "autre-utilisatrice"
ENTRY = {"name": "Suivi de lecture"}


@pytest.fixture
async def mine(env: Env, client: httpx.AsyncClient) -> str:
    """Le projet de January : un rendu avec une vraie capture, évalué et validé (brouillons)."""
    await env.add_profile(1)
    pid = await env.add_project()
    sent = await submit(client, pid, files=shots(("a.png", PNG)))
    assert sent.status_code == 202
    await AgentProjectStore(env.rt).save_review(
        env.user_id, sent.json()["session_id"], pid, outcome()
    )
    assert (await client.get(f"{API}/{pid}/screenshots/1")).content == PNG  # elle existe bien
    return pid


def code(response: httpx.Response) -> str:
    found: str = response.json()["error"]["code"]
    return found


async def test_another_user_cannot_reach_any_route_of_my_project(
    env: Env, app: FastAPI, client: httpx.AsyncClient, mine: str
) -> None:
    unknown = f"{API}/projet-inconnu"
    act_as(app, STRANGER)
    try:
        calls = [
            await client.get(f"{API}/{mine}"),
            await client.get(f"{API}/{mine}/screenshots/1"),
            await client.get(f"{API}/{mine}/screenshots/1", params={"submission": 1}),
            await client.patch(
                f"{API}/{mine}/drafts/cv_line", json={"content": "Pris par l'autre"}
            ),
            await client.post(f"{API}/{mine}/profile-entry", json=ENTRY),
            await submit(client, mine),
            await client.post(f"{API}/{mine}/brief"),
        ]
        for response in calls:
            assert response.status_code == 404 and code(response) == "project_not_found"
        assert (await client.get(f"{unknown}/screenshots/1")).json() == calls[1].json()
        assert (await client.get(API)).json() == []
    finally:
        act_as(app, env.user_id)
    # rien n'a bougé pour January
    row = await env.row(mine)
    assert (row.status, row.profile_version, len(row.submissions)) == ("validated", None, 1)
    assert row.drafts["cv_line"]["edited"] is False
    assert [v.version for v in await env.profile_versions()] == [1]
    assert (await client.get(f"{API}/{mine}/screenshots/1")).content == PNG
