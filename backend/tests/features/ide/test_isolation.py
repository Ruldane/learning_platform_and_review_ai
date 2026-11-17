"""Isolation entre utilisatrices : exercices, séances, exécutions et notes d'une utilisatrice sont
introuvables (404, le même qu'un identifiant inconnu) pour une autre, qui ne peut ni les lire ni
les changer, ni occuper sa place d'exécution."""

from dataclasses import dataclass
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.features.ide.service import file_hash
from tests.features.ide.conftest import OTHER, USER, UseSandbox
from tests.features.ide.support import API, FILES, code, new_session, run_row, start_run
from tests.sessions_support import act_as

pytestmark = pytest.mark.usefixtures("me")

SOURCE = "x = 1\n"


@dataclass
class Mine:
    exercise: str
    session: str
    run: str
    note: str


@pytest.fixture
async def mine(client: httpx.AsyncClient, use_sandbox: UseSandbox) -> Mine:
    """Mon exercice, ma séance, mon exécution en cours et ma proposition ouverte."""
    use_sandbox({"*": ("a", "b")})
    session = await new_session(client, FILES, title="Mon exercice")
    run = (await start_run(client, session["id"])).json()
    await client.put(f"{API}/sessions/{session['id']}/files", json={"files": {"main.py": SOURCE}})
    proposal: dict[str, Any] = {
        "kind": "proposal",
        "content": "Change.",
        "file_path": "main.py",
        "line_start": 1,
        "line_end": 1,
        "replacement": "x = 2",
        "base_hash": file_hash(SOURCE),
    }
    note = await client.post(f"{API}/sessions/{session['id']}/notes", json=proposal)
    return Mine(session["exercise_id"], session["id"], run["id"], note.json()["id"])


async def test_ide_isolation_between_users(
    app: FastAPI, client: httpx.AsyncClient, mine: Mine
) -> None:
    act_as(app, OTHER)
    try:
        sid = mine.session
        calls = [
            await client.delete(f"{API}/exercises/{mine.exercise}"),
            await client.post(f"{API}/sessions", json={"exercise_id": mine.exercise}),
            await client.get(f"{API}/sessions/{sid}"),
            await client.put(f"{API}/sessions/{sid}/files", json={"files": {"main.py": "pris"}}),
            await start_run(client, sid),
            await client.get(f"{API}/runs/{mine.run}"),
            await client.get(f"{API}/sessions/{sid}/notes"),
            await client.post(f"{API}/sessions/{sid}/notes", json={"kind": "hint", "content": "x"}),
            await client.post(f"{API}/notes/{mine.note}/accept"),
            await client.post(f"{API}/notes/{mine.note}/reject"),
            await client.patch(f"{API}/exercises/{mine.exercise}", json={"title": "Pris"}),
        ]
        for response in calls:
            assert response.status_code == 404, response.text
        assert calls[5].json() == (await client.get(f"{API}/runs/inconnue")).json()
        assert code(calls[2]) == "session_not_found" and code(calls[0]) == "exercise_not_found"
        assert (await client.get(f"{API}/exercises")).json() == []
        assert (await client.get(f"{API}/sessions")).json() == []
        # sa place d'exécution est libre malgré mon exécution en cours
        other = await new_session(client)
        assert (await start_run(client, other["id"])).status_code == 202
    finally:
        act_as(app, USER)


async def test_nothing_of_mine_changed_after_the_other_user_tried(
    app: FastAPI, client: httpx.AsyncClient, mine: Mine
) -> None:
    await test_ide_isolation_between_users(app, client, mine)
    got = (await client.get(f"{API}/sessions/{mine.session}")).json()
    assert got["files"] == {"main.py": SOURCE}
    notes = (await client.get(f"{API}/sessions/{mine.session}/notes")).json()
    assert [(n["id"], n["status"]) for n in notes] == [(mine.note, "open")]
    assert (await client.get(f"{API}/exercises")).json()[0]["id"] == mine.exercise
    assert (await run_row(app, mine.run)).status == "running"
    assert len((await client.get(f"{API}/sessions")).json()) == 1
