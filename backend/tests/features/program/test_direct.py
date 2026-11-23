"""Semaines et modules écrits en direct (10.W) : `POST /programs/{id}/weeks`, `PATCH /weeks/{id}`,
`POST /programs/{id}/modules`, `PATCH /modules/{id}`, sans agent ni appel au modèle."""

import httpx
from fastapi import FastAPI

from tests.features.program.support import MONDAY, view
from tests.sessions_support import act_as
from tests.support.direct import API, OTHER, Seed, assert_no_agent

SECRET = "SECRET-DU-PROGRAMME"
WEEK = {"theme": "Évaluation", "objective": "Mesurer un modèle.", "deliverable": "Un rapport"}
MODULE = {"title": "Métriques", "skills": ["Évaluation"], "prerequisites": ["pandas"]}


async def test_add_week_goes_at_the_end_with_the_next_monday(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
) -> None:
    r = await client.post(f"{API}/programs/{drafted.program_id}/weeks", json=WEEK)

    assert r.status_code == 201, r.text
    week = r.json()
    assert (week["rank"], week["theme"], week["modules"]) == (3, "Évaluation", [])
    assert week["start_date"] == "2026-11-30" and week["load_minutes"] == 0  # MONDAY + 14 jours
    program = await view(client, drafted.program_id)
    assert [w["rank"] for w in program["weeks"]] == [1, 2, 3]
    assert program["weeks"][0]["start_date"] == MONDAY.isoformat()
    await assert_no_agent(app)


async def test_patch_week_changes_only_the_given_fields(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
) -> None:
    r = await client.patch(f"{API}/weeks/{drafted.weeks[0]}", json={"theme": "Nouveau thème"})

    assert r.status_code == 200, r.text
    assert (r.json()["theme"], r.json()["objective"]) == ("Nouveau thème", "Savoir faire")
    assert len(r.json()["modules"]) == 1  # ses modules et leurs tâches sont intacts
    await assert_no_agent(app)


async def test_add_module_then_tasks_through_the_existing_patch(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
) -> None:
    r = await client.post(
        f"{API}/programs/{drafted.program_id}/modules", json={**MODULE, "week_id": drafted.weeks[0]}
    )

    assert r.status_code == 201, r.text
    module = r.json()
    assert (module["rank"], module["title"], module["tasks"]) == (1, "Métriques", [])
    assert module["skills"] == ["Évaluation"] and module["prerequisites"] == ["pandas"]
    assert module["lesson_id"] is None and module["skipped"] is False
    tasks = {
        "add_tasks": [
            {
                "module_id": module["id"],
                "title": "Lire sur les métriques",
                "type": "lire",
                "minutes": 30,
                "done_criterion": "Notes prises",
                "planned_date": "2026-11-17",
            }
        ]
    }
    patched = await client.patch(f"{API}/programs/{drafted.program_id}", json=tasks)
    assert patched.status_code == 200, patched.text  # la règle de la semaine est celle de toujours
    program = await view(client, drafted.program_id)
    mine = [m for w in program["weeks"] for m in w["modules"] if m["id"] == module["id"]]
    assert [t["title"] for t in mine[0]["tasks"]] == ["Lire sur les métriques"]
    await assert_no_agent(app)


async def test_patch_module(client: httpx.AsyncClient, app: FastAPI, drafted: Seed) -> None:
    r = await client.patch(
        f"{API}/modules/{drafted.modules[0]}", json={"title": "Bases revues", "skills": ["numpy"]}
    )

    assert r.status_code == 200, r.text
    assert (r.json()["title"], r.json()["skills"]) == ("Bases revues", ["numpy"])
    assert len(r.json()["tasks"]) == 7  # ses tâches restent
    await assert_no_agent(app)


async def test_limits_week_full_and_unknown_week(
    client: httpx.AsyncClient,
    drafted: Seed,
) -> None:
    url = f"{API}/programs/{drafted.program_id}/modules"
    for number in range(3):
        added = await client.post(
            url, json={**MODULE, "title": f"Module {number}", "week_id": drafted.weeks[0]}
        )
        assert added.status_code == 201
    full = await client.post(url, json={**MODULE, "week_id": drafted.weeks[0]})
    assert (full.status_code, full.json()["error"]["code"]) == (409, "week_full")
    unknown = await client.post(url, json={**MODULE, "week_id": "inconnue"})
    assert (unknown.status_code, unknown.json()["error"]["code"]) == (404, "week_not_found")


async def test_invalid_input_is_422_without_echo(
    client: httpx.AsyncClient,
    drafted: Seed,
) -> None:
    calls = [
        client.post(
            f"{API}/programs/{drafted.program_id}/weeks", json={**WEEK, "theme": SECRET * 50}
        ),
        client.post(f"{API}/programs/{drafted.program_id}/weeks", json={"theme": SECRET}),
        client.post(
            f"{API}/programs/{drafted.program_id}/modules",
            json={"week_id": drafted.weeks[0], "title": SECRET * 30, "skills": ["x"]},
        ),
        client.post(
            f"{API}/programs/{drafted.program_id}/modules",
            json={"week_id": drafted.weeks[0], "title": "Titre ok", "skills": []},
        ),
        client.patch(f"{API}/weeks/{drafted.weeks[0]}", json={}),
        client.patch(f"{API}/modules/{drafted.modules[0]}", json={"skills": [SECRET * 50]}),
    ]
    for call in calls:
        r = await call
        assert r.status_code == 422 and SECRET not in r.text


async def test_week_and_module_writes_are_isolated_between_users(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
) -> None:
    act_as(app, OTHER)

    codes = [
        await client.post(f"{API}/programs/{drafted.program_id}/weeks", json=WEEK),
        await client.patch(f"{API}/weeks/{drafted.weeks[0]}", json={"theme": "Pris"}),
        await client.post(
            f"{API}/programs/{drafted.program_id}/modules",
            json={**MODULE, "week_id": drafted.weeks[0]},
        ),
        await client.patch(f"{API}/modules/{drafted.modules[0]}", json={"title": "Pris"}),
    ]

    assert [r.status_code for r in codes] == [404, 404, 404, 404]
    assert [r.json()["error"]["code"] for r in codes] == [
        "program_not_found",
        "week_not_found",
        "program_not_found",
        "module_not_found",
    ]
    act_as(app, drafted.user_id)
    program = await view(client, drafted.program_id)
    assert len(program["weeks"]) == 2 and program["weeks"][0]["theme"] == "Bases"


async def test_patch_week_and_module_carry_the_book_fields(
    client: httpx.AsyncClient, drafted: Seed
) -> None:
    """Un programme existant se remet « de zéro à expert » sans être réécrit : étape et raison de
    la semaine, pages officielles et encadré « code ancien » du module."""
    week = {"stage": "fondations", "rationale": "Le socle de tout le reste."}
    r = await client.patch(f"{API}/weeks/{drafted.weeks[0]}", json=week)
    assert r.status_code == 200, r.text
    assert (r.json()["stage"], r.json()["rationale"]) == ("fondations", week["rationale"])

    url = "https://numpy.org/doc/stable/user/absolute_beginners.html"
    module = {"official_urls": [url], "legacy": ["numpy.matrix"]}
    r = await client.patch(f"{API}/modules/{drafted.modules[0]}", json=module)
    assert r.status_code == 200, r.text
    assert (r.json()["official_urls"], r.json()["legacy"]) == ([url], ["numpy.matrix"])
    r = await client.patch(f"{API}/weeks/{drafted.weeks[0]}", json={"stage": "expert"})
    assert r.status_code == 422, r.text
