"""Routes du programme (D88) : vue complète, liste, isolation entre utilisateurs."""

import httpx
from fastapi import FastAPI

from tests.features.program.conftest import Draft
from tests.features.program.support import (
    API,
    CAP,
    MONDAY,
    WEEK1_LOAD,
    WEEK2_LOAD,
    task_id,
    tasks_of,
    view,
)
from tests.sessions_support import act_as


async def test_program_view_has_week_fields_and_progress(
    client: httpx.AsyncClient, draft_program: Draft
) -> None:
    program = await view(client, draft_program.program_id)
    assert program["title"] == "Parcours données"
    assert program["status"] == "draft" and program["version"] == 1
    assert program["start_date"] == MONDAY.isoformat()
    assert program["session_id"] == "s-draft"
    assert (program["weekly_minutes"], program["cap_minutes"]) == (840, CAP)
    assert (program["weekday_minutes"], program["weekend_minutes"]) == (120, 240)
    first, second = program["weeks"]
    assert (first["theme"], first["objective"], first["deliverable"]) == (
        "Bases",
        "Savoir faire",
        "Un dépôt",
    )
    assert (first["load_minutes"], second["load_minutes"]) == (WEEK1_LOAD, WEEK2_LOAD)
    assert first["load_hours"] == 11.0 and second["load_hours"] == 3.5
    module = first["modules"][0]
    assert module["skills"] == ["pandas"] and module["skipped"] is False
    assert module["lesson_id"] is None and module["resources_count"] == 0
    assert program["progress"] == {
        "done_tasks": 0,
        "total_tasks": 12,
        "done_minutes": 0,
        "total_minutes": WEEK1_LOAD + WEEK2_LOAD,
    }
    assert program["diff"] is None


async def test_list_programs(client: httpx.AsyncClient, draft_program: Draft) -> None:
    r = await client.get(f"{API}/programs")
    assert r.status_code == 200
    [summary] = r.json()
    assert summary["id"] == draft_program.program_id
    assert summary["weeks"] == 2 and summary["progress"]["total_tasks"] == 12


async def test_unknown_program_is_404(client: httpx.AsyncClient) -> None:
    r = await client.get(f"{API}/programs/inconnu")
    assert r.status_code == 404 and r.json()["error"]["code"] == "program_not_found"


async def test_programs_isolated_between_users(
    client: httpx.AsyncClient, app: FastAPI, draft_program: Draft
) -> None:
    program = await view(client, draft_program.program_id)
    tid = task_id(program, "Lire l'article A")
    pid = draft_program.program_id
    act_as(app, "quelqu-un-d-autre")
    try:
        assert (await client.get(f"{API}/programs")).json() == []
        assert (await client.get(f"{API}/programs/{pid}")).status_code == 404
        assert (await client.get(f"{API}/programs/{pid}/export.ics")).status_code == 404
        moved = await client.patch(f"{API}/tasks/{tid}", json={"planned_date": "2026-11-17"})
        assert moved.status_code == 404 and moved.json()["error"]["code"] == "task_not_found"
        patched = await client.patch(f"{API}/programs/{pid}", json={"delete_task_ids": [tid]})
        assert patched.status_code == 404
        assert (await client.post(f"{API}/programs/{pid}/validate")).status_code == 404
    finally:
        app.dependency_overrides.clear()
    after = await view(client, pid)
    assert after["status"] == "draft" and len(tasks_of(after)) == 12
