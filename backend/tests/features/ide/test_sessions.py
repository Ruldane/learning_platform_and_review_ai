"""Exercices et séances de l'IDE : création, ouverture, fichiers (plafonds du bac), suppression."""

from typing import Any

import httpx
import pytest

from app.core.caller import MCP_IDENTITY, McpIdentity
from app.providers.sandbox.base import MAX_FILES, MAX_TOTAL_BYTES
from tests.features.ide.conftest import USER
from tests.features.ide.support import API, FILES, code, new_session

pytestmark = pytest.mark.usefixtures("me")

EXERCISE = {"title": "Boucles", "statement": "Écris une boucle.", "files": FILES}


async def test_exercise_is_created_listed_and_deleted_while_sessions_stay(
    client: httpx.AsyncClient,
) -> None:
    made = await client.post(f"{API}/exercises", json=EXERCISE)
    assert made.status_code == 201
    exercise = made.json()
    assert (exercise["origin"], exercise["topic"], exercise["entry"]) == ("user", None, "main.py")
    session = (await client.post(f"{API}/sessions", json={"exercise_id": exercise["id"]})).json()
    assert [row["id"] for row in (await client.get(f"{API}/exercises")).json()] == [exercise["id"]]
    assert (await client.delete(f"{API}/exercises/{exercise['id']}")).status_code == 204
    assert (await client.get(f"{API}/exercises")).json() == []
    assert (await client.get(f"{API}/sessions/{session['id']}")).status_code == 200
    assert code(await client.delete(f"{API}/exercises/{exercise['id']}")) == "exercise_not_found"


async def test_exercise_added_by_claude_has_origin_claude(client: httpx.AsyncClient) -> None:
    identity = McpIdentity(USER, "t1", "Claude Code", frozenset({"ide"}), "write")
    token = MCP_IDENTITY.set(identity)
    try:
        made = await client.post(f"{API}/exercises", json=EXERCISE)
    finally:
        MCP_IDENTITY.reset(token)
    assert made.json()["origin"] == "claude"


async def test_exercise_entry_is_checked(client: httpx.AsyncClient) -> None:
    for entry in ("../x.py", "/etc/passwd", "a//b.py"):
        response = await client.post(f"{API}/exercises", json={**EXERCISE, "entry": entry})
        assert (response.status_code, code(response)) == (422, "entry_invalid"), entry


async def test_session_opens_on_an_exercise_or_free(client: httpx.AsyncClient) -> None:
    exercise = (await client.post(f"{API}/exercises", json=EXERCISE)).json()
    on = (await client.post(f"{API}/sessions", json={"exercise_id": exercise["id"]})).json()
    assert (on["title"], on["files"], on["entry"]) == ("Boucles", FILES, "main.py")
    assert (on["exercise_id"], on["passed"], on["passed_at"]) == (exercise["id"], False, None)
    free = (await client.post(f"{API}/sessions", json={"title": "Brouillon"})).json()
    assert (free["title"], free["files"]) == ("Brouillon", {"main.py": ""})
    assert free["exercise_id"] is None
    empty = await client.post(f"{API}/exercises", json={"title": "Vide", "statement": "Rien."})
    from_empty = await client.post(f"{API}/sessions", json={"exercise_id": empty.json()["id"]})
    assert from_empty.json()["files"] == {"main.py": ""}
    summaries = (await client.get(f"{API}/sessions")).json()
    assert {row["id"] for row in summaries} == {on["id"], free["id"], from_empty.json()["id"]}
    assert "files" not in summaries[0]


async def test_session_on_unknown_exercise_is_404(client: httpx.AsyncClient) -> None:
    response = await client.post(f"{API}/sessions", json={"exercise_id": "inconnu"})
    assert (response.status_code, code(response)) == (404, "exercise_not_found")


async def test_put_files_replaces_files_and_entry(client: httpx.AsyncClient) -> None:
    session = await new_session(client)
    files = {"main.py": "x = 1\n", "outils.py": "y = 2\n"}
    put = await client.put(f"{API}/sessions/{session['id']}/files", json={"files": files})
    assert (put.status_code, put.json()["files"], put.json()["entry"]) == (200, files, "main.py")
    moved = await client.put(
        f"{API}/sessions/{session['id']}/files", json={"files": files, "entry": "outils.py"}
    )
    assert moved.json()["entry"] == "outils.py"
    got = await client.get(f"{API}/sessions/{session['id']}")
    assert got.json()["files"] == files


async def test_put_files_needs_the_entry_among_the_files(client: httpx.AsyncClient) -> None:
    session = await new_session(client)
    url = f"{API}/sessions/{session['id']}/files"
    for body in ({"files": {"autre.py": "1"}}, {"files": {}}):
        response = await client.put(url, json=body)
        assert (response.status_code, code(response)) == (422, "entry_missing")
    assert (await client.get(f"{API}/sessions/{session['id']}")).json()["files"] == {"main.py": ""}


@pytest.mark.parametrize(
    "files",
    [
        {f"f{i}.py": "" for i in range(MAX_FILES + 1)},
        {"main.py": "x" * (MAX_TOTAL_BYTES + 1)},
        {"main.py": "é" * (MAX_TOTAL_BYTES // 2 + 1)},  # des octets, pas des signes
        {"main.py": "", "../evasion.py": "x"},
        {"main.py": "", "/abs.py": "x"},
    ],
)
async def test_files_limits_enforced(client: httpx.AsyncClient, files: dict[str, str]) -> None:
    session = await new_session(client)
    response = await client.put(f"{API}/sessions/{session['id']}/files", json={"files": files})
    assert (response.status_code, code(response)) == (422, "validation_error")
    assert (await client.get(f"{API}/sessions/{session['id']}")).json()["files"] == {"main.py": ""}


async def test_files_at_the_limits_are_accepted(client: httpx.AsyncClient) -> None:
    session = await new_session(client)
    twenty: dict[str, Any] = {f"f{i}.py": "" for i in range(MAX_FILES - 1)}
    twenty["main.py"] = "x" * MAX_TOTAL_BYTES
    put = await client.put(f"{API}/sessions/{session['id']}/files", json={"files": twenty})
    assert put.status_code == 200 and len(put.json()["files"]) == MAX_FILES
