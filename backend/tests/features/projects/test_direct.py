"""Mini projet écrit en direct (10.W) : `POST /projects` et `PATCH /projects/{id}` rangent l'énoncé
de January ou de Claude comme le port du Praticien, sans agent ni appel au modèle."""

from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.daily import Project
from tests.sessions_support import act_as
from tests.support.direct import API, OTHER, Seed, assert_no_agent

SECRET = "SECRET-DU-PROJET"
BRIEF: dict[str, Any] = {
    "title": "Un pipeline de données",
    "context": "Tu reçois des fichiers CSV de ventes à nettoyer.",
    "objective": "Écrire un pipeline qui produit un fichier propre.",
    "constraints": ["Python seulement", "Pas de service externe"],
    "criteria": ["Le script tourne", "Les doublons sont retirés", "Un test existe"],
    "hours": 4,
    "deliverable": "repo",
}


async def row_of(app: FastAPI, project_id: str) -> Project:
    async with app.state.session_factory() as db:
        found = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one()
        return found


async def test_write_project_is_todo_with_its_brief_and_no_agent(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
) -> None:
    module = drafted.modules[0]
    r = await client.post(f"{API}/projects", json={"module_id": module, "brief": BRIEF})

    assert r.status_code == 201, r.text
    project = r.json()
    assert (project["status"], project["title"], project["module_id"]) == (
        "todo",
        "Un pipeline de données",
        module,
    )
    assert project["program_id"] == drafted.program_id and project["session_id"] is None
    assert project["brief"] == BRIEF and project["submissions"] == []
    listed = (await client.get(f"{API}/projects")).json()
    assert [(row["id"], row["hours"], row["week"]) for row in listed] == [(project["id"], 4, 1)]
    assert (await client.get(f"{API}/projects/{project['id']}")).json()["brief"] == BRIEF
    await assert_no_agent(app)


async def test_second_project_for_a_module_is_refused(
    client: httpx.AsyncClient,
    drafted: Seed,
) -> None:
    body = {"module_id": drafted.modules[0], "brief": BRIEF}
    assert (await client.post(f"{API}/projects", json=body)).status_code == 201

    again = await client.post(f"{API}/projects", json=body)

    assert (again.status_code, again.json()["error"]["code"]) == (409, "project_exists")


async def test_patch_project_replaces_the_given_fields(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
) -> None:
    made = await client.post(
        f"{API}/projects", json={"module_id": drafted.modules[0], "brief": BRIEF}
    )
    project_id = made.json()["id"]

    r = await client.patch(
        f"{API}/projects/{project_id}", json={"title": "Pipeline revu", "hours": 5}
    )

    assert r.status_code == 200, r.text
    assert (r.json()["title"], r.json()["brief"]["hours"]) == ("Pipeline revu", 5)
    assert r.json()["brief"]["criteria"] == BRIEF["criteria"] and r.json()["status"] == "todo"
    assert (await row_of(app, project_id)).title == "Pipeline revu"
    await assert_no_agent(app)


async def test_a_project_without_brief_receives_it_whole_and_a_rendered_one_is_closed(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
) -> None:
    async with app.state.session_factory() as db:
        row = Project(
            user_id=drafted.user_id,
            module_id=drafted.modules[0],
            program_id=drafted.program_id,
            title="Module Bases",
            status="brief_failed",
        )
        db.add(row)
        await db.commit()
        project_id = row.id
    partial = await client.patch(f"{API}/projects/{project_id}", json={"title": "Un titre"})
    assert partial.status_code == 422 and partial.json()["error"]["details"]["fields"]

    whole = await client.patch(f"{API}/projects/{project_id}", json=BRIEF)
    assert whole.status_code == 200 and whole.json()["status"] == "todo"
    async with app.state.session_factory() as db:
        stored = await db.get(Project, project_id)
        assert stored is not None
        stored.status = "validated"
        await db.commit()

    closed = await client.patch(f"{API}/projects/{project_id}", json={"hours": 3})

    assert (closed.status_code, closed.json()["error"]["code"]) == (409, "project_not_editable")


async def test_invalid_brief_is_422_without_echo(
    client: httpx.AsyncClient,
    drafted: Seed,
) -> None:
    module = drafted.modules[0]
    bad = [
        {**BRIEF, "criteria": [SECRET, SECRET]},
        {**BRIEF, "title": SECRET * 40},
        {**BRIEF, "hours": 30, "context": SECRET},
        {**BRIEF, "deliverable": SECRET},
    ]
    for brief in bad:
        r = await client.post(f"{API}/projects", json={"module_id": module, "brief": brief})
        assert r.status_code == 422 and SECRET not in r.text
    made = await client.post(f"{API}/projects", json={"module_id": module, "brief": BRIEF})
    patches = [{"criteria": [SECRET]}, {"constraints": [SECRET * 40, SECRET]}, {"hours": 99}]
    for patch in patches:
        r = await client.patch(f"{API}/projects/{made.json()['id']}", json=patch)
        assert r.status_code == 422 and SECRET not in r.text


async def test_project_write_is_isolated_between_users(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
) -> None:
    made = await client.post(
        f"{API}/projects", json={"module_id": drafted.modules[0], "brief": BRIEF}
    )
    project_id = made.json()["id"]
    act_as(app, OTHER)

    other_write = await client.post(
        f"{API}/projects", json={"module_id": drafted.modules[1], "brief": BRIEF}
    )
    other_patch = await client.patch(f"{API}/projects/{project_id}", json={"hours": 6})

    assert (other_write.status_code, other_write.json()["error"]["code"]) == (
        404,
        "module_not_found",
    )
    assert (other_patch.status_code, other_patch.json()["error"]["code"]) == (
        404,
        "project_not_found",
    )
    assert (await row_of(app, project_id)).brief["hours"] == 4
