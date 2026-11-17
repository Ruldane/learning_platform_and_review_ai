"""Notes de séance : l'auteur suit l'appelant ; une proposition remplace une plage de lignes si le
fichier n'a pas changé (empreinte sha256), sinon elle est périmée ; accepter et refuser."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.core.caller import MCP_IDENTITY, McpIdentity
from app.db.models.ide import IdeSession
from app.features.ide.service import file_hash
from tests.features.ide.conftest import USER
from tests.features.ide.support import API, code, new_session

pytestmark = pytest.mark.usefixtures("me")

SOURCE = "def f(n):\n    return n + 1\n\nprint(f(1))\n"


@pytest.fixture
async def session(client: httpx.AsyncClient) -> dict[str, Any]:
    return await new_session(client, {"main.py": SOURCE, "outils.py": "x = 1\n"})


def proposal(**over: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "kind": "proposal",
        "content": "Double la valeur.",
        "file_path": "main.py",
        "line_start": 2,
        "line_end": 2,
        "replacement": "    return n * 2",
        "base_hash": file_hash(SOURCE),
    }
    return {**body, **over}


async def statuses(client: httpx.AsyncClient, session_id: str) -> dict[str, str]:
    notes = (await client.get(f"{API}/sessions/{session_id}/notes")).json()
    return {n["id"]: n["status"] for n in notes}


async def post(client: httpx.AsyncClient, session_id: str, body: dict[str, Any]) -> httpx.Response:
    return await client.post(f"{API}/sessions/{session_id}/notes", json=body)


@contextmanager
def acting_as_claude() -> Iterator[None]:
    """Les requêtes qui suivent passent par le MCP (identité posée par l'envoyeur, jamais par un
    en-tête)."""
    token = MCP_IDENTITY.set(McpIdentity(USER, "t1", "Claude Code", frozenset({"ide"}), "write"))
    try:
        yield
    finally:
        MCP_IDENTITY.reset(token)


async def test_add_note_author_follows_caller(
    client: httpx.AsyncClient, session: dict[str, Any]
) -> None:
    first = (await post(client, session["id"], {"kind": "hint", "content": "Relis."})).json()
    with acting_as_claude():
        second = (
            await post(client, session["id"], {"kind": "hint", "content": "Pense aux cas."})
        ).json()
    assert (first["author"], first["author_label"]) == ("user", None)
    assert (second["author"], second["author_label"]) == ("claude", "Claude Code")
    assert first["status"] == "open" and first["reference_note_id"] is None
    notes = (await client.get(f"{API}/sessions/{session['id']}/notes")).json()
    assert [n["id"] for n in notes] == [first["id"], second["id"]]  # les plus anciennes d'abord


async def test_author_cannot_be_forged_by_the_body(
    client: httpx.AsyncClient, session: dict[str, Any]
) -> None:
    sent = await post(
        client, session["id"], {"kind": "hint", "content": "x", "author": "professor"}
    )
    assert sent.status_code == 201 and sent.json()["author"] == "user"


async def test_annotation_on_a_line_and_its_checks(
    client: httpx.AsyncClient, session: dict[str, Any]
) -> None:
    note = {"kind": "annotation", "content": "Ici.", "file_path": "main.py", "line_start": 2}
    assert (await post(client, session["id"], note)).status_code == 201
    for bad in (
        {"file_path": "absent.py"},
        {"line_start": 99},
        {"line_start": 3, "line_end": 2},
        {"line_end": 3, "line_start": None},
        {"file_path": None},  # des lignes sans fichier
        {"replacement": "x"},  # seul une proposition remplace
        {"base_hash": "a" * 64},
    ):
        response = await post(client, session["id"], {**note, **bad})
        assert (response.status_code, code(response)) == (422, "note_invalid"), bad


async def test_proposal_needs_valid_range_and_base_hash(
    client: httpx.AsyncClient, session: dict[str, Any]
) -> None:
    assert (await post(client, session["id"], proposal())).status_code == 201
    for bad in (
        {"file_path": None},
        {"line_start": None},
        {"replacement": None},
        {"line_start": 5, "line_end": 5},  # le fichier n'a que 4 lignes
        {"line_start": 3, "line_end": 2},
        {"file_path": "absent.py"},
    ):
        response = await post(client, session["id"], proposal(**bad))
        assert (response.status_code, code(response)) == (422, "note_invalid"), bad
    missing = await post(client, session["id"], proposal(base_hash=None))
    assert (missing.status_code, code(missing)) == (422, "note_invalid")
    assert missing.json()["error"]["details"] == {"file_hash": file_hash(SOURCE)}  # pour réessayer
    for malformed in ("A" * 64, "g" * 64, "ab" * 32 + "0"):
        response = await post(client, session["id"], proposal(base_hash=malformed))
        assert response.status_code == 422, malformed
    stale = await post(client, session["id"], proposal(base_hash="0" * 64))
    assert (stale.status_code, code(stale)) == (409, "note_stale")
    assert stale.json()["error"]["details"] == {"file_hash": file_hash(SOURCE)}


async def test_accept_applies_replacement_and_marks_other_open_proposals_stale(
    client: httpx.AsyncClient, session: dict[str, Any]
) -> None:
    one = (await post(client, session["id"], proposal())).json()
    two = (await post(client, session["id"], proposal(replacement="    return n - 1"))).json()
    other_file = (
        await post(
            client,
            session["id"],
            proposal(
                file_path="outils.py",
                line_start=1,
                line_end=1,
                replacement="x = 2",
                base_hash=file_hash("x = 1\n"),
            ),
        )
    ).json()
    accepted = await client.post(f"{API}/notes/{one['id']}/accept")
    assert accepted.status_code == 200
    assert accepted.json()["files"]["main.py"] == "def f(n):\n    return n * 2\n\nprint(f(1))\n"
    assert accepted.json()["files"]["outils.py"] == "x = 1\n"
    status = await statuses(client, session["id"])
    assert status == {one["id"]: "accepted", two["id"]: "stale", other_file["id"]: "open"}
    got = (await client.get(f"{API}/sessions/{session['id']}")).json()
    assert got["files"]["main.py"].splitlines()[1] == "    return n * 2"


async def test_accept_multi_line_range_and_deletion(
    client: httpx.AsyncClient, session: dict[str, Any]
) -> None:
    note = (
        await post(
            client,
            session["id"],
            proposal(line_start=1, line_end=2, replacement="def f(n):\n    return n\n"),
        )
    ).json()
    files = (await client.post(f"{API}/notes/{note['id']}/accept")).json()["files"]
    assert files["main.py"] == "def f(n):\n    return n\n\nprint(f(1))\n"
    again = (await client.get(f"{API}/sessions/{session['id']}")).json()["files"]["main.py"]
    drop = (
        await post(
            client,
            session["id"],
            proposal(
                line_start=3, line_end=4, replacement="", base_hash=file_hash(again), content="Sup."
            ),
        )
    ).json()
    files = (await client.post(f"{API}/notes/{drop['id']}/accept")).json()["files"]
    assert files["main.py"] == "def f(n):\n    return n\n"


async def test_accept_stale_proposal_refused(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any]
) -> None:
    note = (await post(client, session["id"], proposal())).json()
    # le fichier est modifié sans passer par `PUT` (la note reste ouverte en base)
    async with app.state.session_factory() as db:
        row = await db.get(IdeSession, session["id"])
        assert row is not None
        row.files = {**row.files, "main.py": SOURCE + "# changé\n"}
        await db.commit()
    refused = await client.post(f"{API}/notes/{note['id']}/accept")
    assert (refused.status_code, code(refused)) == (409, "note_stale")
    assert refused.json()["error"]["details"] == {"file_hash": file_hash(SOURCE + "# changé\n")}
    notes = (await client.get(f"{API}/sessions/{session['id']}/notes")).json()
    assert notes[0]["status"] == "stale"  # enregistré malgré l'erreur
    got = (await client.get(f"{API}/sessions/{session['id']}")).json()
    assert got["files"]["main.py"] == SOURCE + "# changé\n"  # rien n'a été écrit
    assert code(await client.post(f"{API}/notes/{note['id']}/accept")) == "note_stale"


async def test_saving_files_marks_changed_proposals_stale(
    client: httpx.AsyncClient, session: dict[str, Any]
) -> None:
    on_main = (await post(client, session["id"], proposal())).json()
    on_tools = (
        await post(
            client,
            session["id"],
            proposal(
                file_path="outils.py",
                line_start=1,
                line_end=1,
                replacement="x = 3",
                base_hash=file_hash("x = 1\n"),
            ),
        )
    ).json()
    put = await client.put(
        f"{API}/sessions/{session['id']}/files",
        json={"files": {"main.py": SOURCE + "\n# ajout\n", "outils.py": "x = 1\n"}},
    )
    assert put.status_code == 200
    status = await statuses(client, session["id"])
    assert status == {on_main["id"]: "stale", on_tools["id"]: "open"}


async def test_reject_and_closed_proposals(
    client: httpx.AsyncClient, session: dict[str, Any]
) -> None:
    one = (await post(client, session["id"], proposal())).json()
    rejected = await client.post(f"{API}/notes/{one['id']}/reject")
    assert (rejected.status_code, rejected.json()["status"]) == (200, "rejected")
    after = await client.post(f"{API}/notes/{one['id']}/accept")
    assert (after.status_code, code(after)) == (409, "note_closed")
    files = (await client.get(f"{API}/sessions/{session['id']}")).json()["files"]
    assert files["main.py"] == SOURCE
    two = (await post(client, session["id"], proposal())).json()
    assert (await client.post(f"{API}/notes/{two['id']}/accept")).status_code == 200
    again = await client.post(f"{API}/notes/{two['id']}/reject")
    assert (again.status_code, code(again)) == (409, "note_closed")
    hint = (await post(client, session["id"], {"kind": "hint", "content": "Indice."})).json()
    for verb in ("accept", "reject"):
        response = await client.post(f"{API}/notes/{hint['id']}/{verb}")
        assert (response.status_code, code(response)) == (409, "not_a_proposal")


async def test_accept_refuses_a_result_beyond_the_size_limit(
    client: httpx.AsyncClient,
) -> None:
    big = "x" * 199_000
    session = await new_session(client, {"main.py": "a\n", "grand.py": big})
    note = (
        await post(
            client,
            session["id"],
            proposal(
                line_start=1,
                line_end=1,
                replacement="y" * 3_000,
                base_hash=file_hash("a\n"),
                content="Long.",
            ),
        )
    ).json()
    refused = await client.post(f"{API}/notes/{note['id']}/accept")
    assert (refused.status_code, code(refused)) == (422, "files_too_large")


async def test_unknown_session_or_note_is_404(client: httpx.AsyncClient) -> None:
    unknown = await post(client, "inconnue", {"kind": "hint", "content": "x"})
    assert (unknown.status_code, code(unknown)) == (404, "session_not_found")
    assert code(await client.get(f"{API}/sessions/inconnue/notes")) == "session_not_found"
    for verb in ("accept", "reject"):
        response = await client.post(f"{API}/notes/inconnue/{verb}")
        assert (response.status_code, code(response)) == (404, "note_not_found")
