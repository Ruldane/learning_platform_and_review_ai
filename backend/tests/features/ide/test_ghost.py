"""Les vérifications personnelles gardent leur durée et la version de départ."""

import httpx
import pytest
from fastapi import FastAPI

from app.features.ide.mcp import MCP
from app.providers.sandbox.base import SandboxResult
from tests.features.ide.conftest import OTHER, UseSandbox
from tests.features.ide.support import API, new_session, start_run
from tests.sessions_support import act_as

pytestmark = pytest.mark.usefixtures("me")


async def test_ghost_reads_finished_checks_on_the_same_exercise(
    client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": SandboxResult(status="done", exit_code=1, duration_ms=1450, truncated=False)})
    first = await new_session(client, title="Calcul simple")
    exercise_id = first["exercise_id"]
    started = await start_run(client, first["id"], "check")
    assert started.status_code == 202
    run_id = started.json()["id"]
    assert await history(client, first["id"]) == []
    assert (await client.get(f"{API}/runs/{run_id}")).status_code == 200
    output_run = await start_run(client, first["id"], "run")
    assert (await client.get(f"{API}/runs/{output_run.json()['id']}")).status_code == 200

    same = await open_session(client, exercise_id)
    (summary,) = await history(client, same)
    assert {k: v for k, v in summary.items() if k != "created_at"} == {
        "id": run_id,
        "version": "same",
        "elapsed_ms": 1450,
        "errors": 1,
        "progress": 0,
        "total": 1,
        "score_percent": None,
    }

    patched = await client.patch(
        f"{API}/exercises/{exercise_id}", json={"statement": "Vérifie aussi un cas vide."}
    )
    assert patched.status_code == 200
    retained = await client.get(f"{API}/sessions/{first['id']}")
    assert retained.json()["exercise_statement"] == "Écris une fonction."
    changed = await open_session(client, exercise_id)
    assert [item["version"] for item in await history(client, changed)] == ["changed"]
    assert await history(client, (await new_session(client))["id"]) == []


def test_ide_session_actions_fence_exercise_statement() -> None:
    returning_session = {
        "ide_create_session",
        "ide_get_session",
        "ide_write_file",
        "ide_create_project_file",
        "ide_rename_project_file",
        "ide_delete_project_file",
    }
    actions = {action.name: action for action in MCP.actions}
    assert all("exercise_statement" in actions[name].untrusted for name in returning_session)


async def test_journal_links_only_a_concluded_check(
    app: FastAPI, client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": ("Sortie privée de test.", "Fin.")})
    session = await new_session(client, title="Vérification à retrouver")
    sid = session["id"]
    run = await start_run(client, sid, "check")
    run_id = run.json()["id"]
    assert (await client.get(f"{API}/runs/{run_id}")).json()["status"] == "running"
    journal = "/api/v1/journal"
    assert (await client.get(journal)).json()["entries"] == []
    assert (await client.get(f"{API}/runs/{run_id}")).json()["status"] == "done"
    assert (await client.get(f"{API}/runs/{run_id}")).json()["status"] == "done"

    response = await client.get(journal)
    assert response.status_code == 200
    (entry,) = response.json()["entries"]
    assert entry["kind"] == "ide_check"
    assert entry["links"]["ide_session_id"] == sid
    assert entry["links"]["ide_run_id"] == run_id
    assert "Sortie privée" not in response.text
    selected = await client.get(f"{API}/sessions/{sid}/ghost", params={"run_id": run_id})
    assert selected.json()[0]["id"] == run_id
    assert "Sortie privée" not in selected.text
    act_as(app, OTHER)
    assert (await client.get(journal)).json()["entries"] == []
    assert (
        await client.get(f"{API}/sessions/{sid}/ghost", params={"run_id": run_id})
    ).status_code == 404


async def open_session(client: httpx.AsyncClient, exercise_id: str) -> str:
    res = await client.post(f"{API}/sessions", json={"exercise_id": exercise_id})
    assert res.status_code == 201
    return str(res.json()["id"])


async def history(client: httpx.AsyncClient, session_id: str) -> list[dict[str, object]]:
    res = await client.get(f"{API}/sessions/{session_id}/ghost")
    assert res.status_code == 200
    return list(res.json())
