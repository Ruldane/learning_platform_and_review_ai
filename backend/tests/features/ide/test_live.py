"""Le direct (10.X) : l'origine (`app` ou `mcp`) d'une exécution et d'une note, et la liste des
dernières exécutions d'une séance (la page de séance la relit toutes les 3 s)."""

import httpx
import pytest
from fastapi import FastAPI

from tests.features.ide.conftest import OTHER, UseSandbox
from tests.features.ide.mcp_support import acting_as_claude
from tests.features.ide.support import API, code, new_session, run_row, start_run
from tests.sessions_support import act_as

pytestmark = pytest.mark.usefixtures("me")

NOTE = {"kind": "hint", "content": "Relis la ligne du retour."}


async def test_run_origin_follows_the_caller(
    app: FastAPI, client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": "ok"})
    session = await new_session(client)
    mine = (await start_run(client, session["id"])).json()
    assert mine["origin"] == "app"
    await client.get(f"{API}/runs/{mine['id']}")  # fin lue : la place est libre
    with acting_as_claude():
        theirs = (await start_run(client, session["id"])).json()
    assert theirs["origin"] == "mcp"
    assert (await run_row(app, theirs["id"])).origin == "mcp"
    assert (await run_row(app, mine["id"])).origin == "app"


async def test_note_origin_follows_the_caller(client: httpx.AsyncClient) -> None:
    session = await new_session(client)
    url = f"{API}/sessions/{session['id']}/notes"
    first = (await client.post(url, json=NOTE)).json()
    with acting_as_claude():
        second = (await client.post(url, json=NOTE)).json()
    assert (first["origin"], second["origin"]) == ("app", "mcp")
    listed = {n["id"]: n["origin"] for n in (await client.get(url)).json()}
    assert listed == {first["id"]: "app", second["id"]: "mcp"}


async def test_origin_cannot_be_forged_by_the_body(
    client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": "ok"})
    session = await new_session(client)
    note = await client.post(
        f"{API}/sessions/{session['id']}/notes", json={**NOTE, "origin": "mcp"}
    )
    assert note.json()["origin"] == "app"
    run = await client.post(
        f"{API}/sessions/{session['id']}/runs", json={"kind": "run", "origin": "mcp"}
    )
    assert run.json()["origin"] == "app"


async def test_runs_list_is_newest_first_and_capped_at_20(
    client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": "ok"})
    session = await new_session(client)
    ids: list[str] = []
    for _ in range(22):
        run = (await start_run(client, session["id"])).json()
        await client.get(f"{API}/runs/{run['id']}")
        ids.append(run["id"])
    listed = (await client.get(f"{API}/sessions/{session['id']}/runs")).json()
    assert [r["id"] for r in listed] == ids[::-1][:20]
    assert set(listed[0]) == {"id", "session_id", "kind", "entry", "status", "created_at", "origin"}


async def test_runs_list_is_scoped_to_the_session(
    client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": "ok"})
    one, two = await new_session(client), await new_session(client)
    run = (await start_run(client, one["id"])).json()
    await client.get(f"{API}/runs/{run['id']}")
    assert [r["id"] for r in (await client.get(f"{API}/sessions/{one['id']}/runs")).json()] == [
        run["id"]
    ]
    assert (await client.get(f"{API}/sessions/{two['id']}/runs")).json() == []


async def test_runs_list_of_another_user_is_404(
    app: FastAPI, client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": "ok"})
    session = await new_session(client)
    act_as(app, OTHER)
    gone = await client.get(f"{API}/sessions/{session['id']}/runs")
    assert (gone.status_code, code(gone)) == (404, "session_not_found")
    unknown = await client.get(f"{API}/sessions/inconnue/runs")
    assert gone.json() == unknown.json()
