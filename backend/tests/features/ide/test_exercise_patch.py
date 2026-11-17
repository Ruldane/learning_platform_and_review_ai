"""Retouche d'un exercice de l'IDE (10.W) : `PATCH /ide/exercises/{id}` change l'énoncé, les
fichiers de départ et de test pytest, sans agent, sans exécution et sans changer l'origine."""

from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.core.caller import MCP_IDENTITY, McpIdentity
from app.providers.sandbox.base import MAX_FILES, MAX_TOTAL_BYTES
from tests.features.ide.conftest import OTHER, USER, UseSandbox
from tests.features.ide.support import API, FILES, code
from tests.features.ide.teach_support import ScriptedModels
from tests.sessions_support import act_as
from tests.support.direct import assert_no_agent

pytestmark = pytest.mark.usefixtures("me")

SECRET = "SECRET-DE-L-EXERCICE"
EXERCISE = {"title": "Boucles", "statement": "Écris une boucle.", "files": FILES}
TESTS = {
    "test_boucles.py": (
        "from main import boucle\n\n\ndef test_boucle():\n    assert boucle(2) == 2\n"
    )
}


async def make(client: httpx.AsyncClient) -> dict[str, Any]:
    made = await client.post(f"{API}/exercises", json=EXERCISE)
    assert made.status_code == 201
    body: dict[str, Any] = made.json()
    return body


async def test_patch_changes_the_given_fields_only(
    client: httpx.AsyncClient, app: FastAPI, use_sandbox: UseSandbox, models: ScriptedModels
) -> None:
    fake = use_sandbox({"*": "ne doit jamais tourner"})
    exercise = await make(client)
    files = {"main.py": "def boucle(n):\n    return n\n", **TESTS}

    r = await client.patch(
        f"{API}/exercises/{exercise['id']}",
        json={"statement": "Écris `boucle(n)`.", "files": files, "title": "Boucles 2"},
    )

    assert r.status_code == 200, r.text
    patched = r.json()
    assert (patched["title"], patched["statement"], patched["files"]) == (
        "Boucles 2",
        "Écris `boucle(n)`.",
        files,
    )
    assert (patched["entry"], patched["origin"], patched["id"]) == (
        "main.py",
        "user",
        exercise["id"],
    )
    assert [row["files"] for row in (await client.get(f"{API}/exercises")).json()] == [files]
    session = await client.post(f"{API}/sessions", json={"exercise_id": exercise["id"]})
    assert (
        session.json()["files"] == files
    )  # les séances ouvertes ensuite partent des nouveaux fichiers
    assert fake._runs == {}  # rien n'a été exécuté
    assert models.calls == []  # aucun modèle demandé
    await assert_no_agent(app)


async def test_patch_by_claude_marks_the_exercise_as_claudes(client: httpx.AsyncClient) -> None:
    exercise = await make(client)
    identity = McpIdentity(USER, "t1", "Claude Code", frozenset({"ide"}), "write")
    token = MCP_IDENTITY.set(identity)
    try:
        r = await client.patch(
            f"{API}/exercises/{exercise['id']}", json={"statement": "Nouvel énoncé."}
        )
    finally:
        MCP_IDENTITY.reset(token)

    assert r.status_code == 200 and r.json()["origin"] == "claude"


async def test_files_and_entry_keep_the_exercise_runnable(client: httpx.AsyncClient) -> None:
    exercise = await make(client)
    url = f"{API}/exercises/{exercise['id']}"

    for body in ({"files": {"autre.py": "x = 1\n"}}, {"entry": "absent.py"}):
        r = await client.patch(url, json=body)
        assert (r.status_code, code(r)) == (422, "entry_invalid"), body
    created = await client.post(f"{API}/exercises", json={**EXERCISE, "files": {"x.py": "x = 1\n"}})
    assert (created.status_code, code(created)) == (422, "entry_invalid")
    ok = await client.patch(url, json={"files": {"autre.py": "x = 1\n"}, "entry": "autre.py"})
    assert ok.status_code == 200 and ok.json()["entry"] == "autre.py"


async def test_patch_is_checked_like_a_creation(client: httpx.AsyncClient) -> None:
    exercise = await make(client)
    url = f"{API}/exercises/{exercise['id']}"

    for entry in ("../x.py", "/etc/passwd", "a//b.py"):
        r = await client.patch(url, json={"entry": entry})
        assert (r.status_code, code(r)) == (422, "entry_invalid"), entry
    too_many = {f"f{i}.py": "x = 1\n" for i in range(MAX_FILES + 1)}
    too_big = {"main.py": SECRET * (MAX_TOTAL_BYTES // len(SECRET) + 1)}
    bad_path = {"../" + SECRET: "x = 1\n"}
    for body in (
        {"files": too_many},
        {"files": too_big},
        {"files": bad_path},
        {},
        {"statement": SECRET * 5_000},
        {"title": ""},
    ):
        r = await client.patch(url, json=body)
        assert r.status_code == 422 and SECRET not in r.text
    assert (await client.get(f"{API}/exercises")).json()[0]["files"] == FILES  # rien n'a changé


async def test_patch_of_another_users_exercise_is_404(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    exercise = await make(client)
    act_as(app, OTHER)

    r = await client.patch(f"{API}/exercises/{exercise['id']}", json={"title": "Pris"})

    assert (r.status_code, code(r)) == (404, "exercise_not_found")
    act_as(app, USER)
    assert (await client.get(f"{API}/exercises")).json()[0]["title"] == "Boucles"
