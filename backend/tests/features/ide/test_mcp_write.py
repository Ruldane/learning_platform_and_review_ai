"""Claude écrit dans les fichiers (10.X), sous l'interrupteur de January : refusé tant qu'il est
éteint (403, rien d'écrit), `base_hash` exigé (jamais d'écrasement de sa frappe : 409), un seul
fichier à la fois, et seule l'interface règle l'interrupteur."""

import hashlib
import logging

import httpx
import pytest
from fastapi import FastAPI

from app.features.ide.service import file_hash
from tests.features.ide.conftest import OTHER, USER
from tests.features.ide.mcp_support import acting_as_claude, set_switch, write
from tests.features.ide.support import API, code, new_session
from tests.sessions_support import act_as

pytestmark = pytest.mark.usefixtures("me")

SECRET = "mot_de_passe_dans_le_code = 'NE-JAMAIS-JOURNALISER'\n"
FILES = {"main.py": SECRET, "outils.py": "x = 1\n"}
EMPTY_HASH = hashlib.sha256(b"").hexdigest()


async def files_of(client: httpx.AsyncClient, session_id: str) -> dict[str, str]:
    got = (await client.get(f"{API}/sessions/{session_id}")).json()
    files: dict[str, str] = got["files"]
    return files


# --- l'interrupteur -----------------------------------------------------------------------


async def test_switch_is_off_by_default_and_set_from_the_interface(
    client: httpx.AsyncClient,
) -> None:
    assert (await client.get(f"{API}/preferences")).json()["mcp_can_write_files"] is False
    await set_switch(client, True)
    assert (await client.get(f"{API}/preferences")).json()["mcp_can_write_files"] is True
    await set_switch(client, False)
    assert (await client.get(f"{API}/preferences")).json()["mcp_can_write_files"] is False


async def test_omitting_the_switch_in_a_put_turns_it_off(client: httpx.AsyncClient) -> None:
    await set_switch(client, True)
    body = {"teacher_mode": "auto", "session_cap": 5000, "day_cap": 9000}
    saved = await client.put(f"{API}/preferences", json=body)
    assert saved.json()["mcp_can_write_files"] is False  # défaut sûr : éteint


async def test_claude_cannot_change_the_switch(client: httpx.AsyncClient) -> None:
    with acting_as_claude():
        refused = await client.put(
            f"{API}/preferences", json={"teacher_mode": "auto", "mcp_can_write_files": True}
        )
    assert refused.status_code == 403
    assert (await client.get(f"{API}/preferences")).json()["mcp_can_write_files"] is False


# --- écriture refusée, éteint -------------------------------------------------------------


async def test_write_is_403_when_off_and_nothing_is_written(
    client: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    session = await new_session(client, FILES)
    caplog.set_level(logging.INFO)
    with acting_as_claude():
        refused = await write(
            client, session["id"], {"main.py": "pris = 1\n"}, base_hash=file_hash(SECRET)
        )
    assert (refused.status_code, code(refused)) == (403, "mcp_ide_write_off")
    assert "interrupteur" in refused.json()["error"]["message"].lower()
    assert "NE-JAMAIS-JOURNALISER" not in refused.text and "pris" not in refused.text
    assert await files_of(client, session["id"]) == FILES
    assert any("mcp_ide_write_off" in r.getMessage() for r in caplog.records)
    assert "NE-JAMAIS-JOURNALISER" not in caplog.text and "pris = 1" not in caplog.text


async def test_the_interface_still_writes_when_the_switch_is_off(client: httpx.AsyncClient) -> None:
    session = await new_session(client, FILES)
    saved = await write(client, session["id"], {"main.py": "a = 2\n"})
    assert saved.status_code == 200
    assert await files_of(client, session["id"]) == {"main.py": "a = 2\n"}  # tout remplacé


# --- écriture permise ----------------------------------------------------------------------


async def test_write_is_accepted_when_on_and_keeps_the_other_files(
    client: httpx.AsyncClient,
) -> None:
    session = await new_session(client, FILES)
    await set_switch(client, True)
    with acting_as_claude():
        done = await write(
            client, session["id"], {"main.py": "x = 2\n"}, base_hash=file_hash(SECRET)
        )
    assert done.status_code == 200, done.text
    assert done.json()["files"] == {"main.py": "x = 2\n", "outils.py": "x = 1\n"}
    assert done.json()["entry"] == session["entry"]
    assert await files_of(client, session["id"]) == {"main.py": "x = 2\n", "outils.py": "x = 1\n"}


async def test_session_exposes_the_hash_of_each_file(client: httpx.AsyncClient) -> None:
    session = await new_session(client, FILES)
    got = (await client.get(f"{API}/sessions/{session['id']}")).json()
    assert got["file_hashes"] == {name: file_hash(text) for name, text in FILES.items()}
    assert session["file_hashes"] == got["file_hashes"]


async def test_a_new_file_is_written_with_the_hash_of_the_empty_text(
    client: httpx.AsyncClient,
) -> None:
    session = await new_session(client, FILES)
    await set_switch(client, True)
    with acting_as_claude():
        done = await write(client, session["id"], {"neuf.py": "y = 3\n"}, base_hash=EMPTY_HASH)
        again = await write(client, session["id"], {"neuf.py": "y = 4\n"}, base_hash=EMPTY_HASH)
    assert done.status_code == 200 and done.json()["files"]["neuf.py"] == "y = 3\n"
    assert (again.status_code, code(again)) == (409, "stale_base")
    assert (await files_of(client, session["id"]))["neuf.py"] == "y = 3\n"


# --- jamais écraser sa frappe --------------------------------------------------------------


async def test_a_stale_base_hash_is_409_and_nothing_is_written(client: httpx.AsyncClient) -> None:
    session = await new_session(client, FILES)
    await set_switch(client, True)
    stale = file_hash(SECRET)
    typed = "def f():\n    return 1\n"  # January a continué à écrire depuis la lecture de Claude
    assert (
        await write(client, session["id"], {"main.py": typed, "outils.py": "x = 1\n"})
    ).is_success
    with acting_as_claude():
        refused = await write(client, session["id"], {"main.py": "ecrase = 1\n"}, base_hash=stale)
    assert (refused.status_code, code(refused)) == (409, "stale_base")
    assert "relis" in refused.json()["error"]["message"].lower()
    assert file_hash(typed) not in refused.text  # la nouvelle empreinte n'est pas donnée : il relit
    assert (await files_of(client, session["id"]))["main.py"] == typed


async def test_the_hash_is_required_and_must_be_well_formed(client: httpx.AsyncClient) -> None:
    session = await new_session(client, FILES)
    await set_switch(client, True)
    with acting_as_claude():
        missing = await write(client, session["id"], {"main.py": "z = 1\n"})
        malformed = await write(client, session["id"], {"main.py": "z = 1\n"}, base_hash="abc")
        upper = await write(
            client, session["id"], {"main.py": "z = 1\n"}, base_hash=file_hash(SECRET).upper()
        )
    assert (missing.status_code, code(missing)) == (422, "base_hash_required")
    assert malformed.status_code == 422  # le schéma : 64 signes
    assert (upper.status_code, code(upper)) == (422, "base_hash_required")
    assert await files_of(client, session["id"]) == FILES


async def test_claude_writes_one_file_at_a_time(client: httpx.AsyncClient) -> None:
    session = await new_session(client, FILES)
    await set_switch(client, True)
    with acting_as_claude():
        two = await write(
            client,
            session["id"],
            {"main.py": "a = 1\n", "outils.py": "b = 2\n"},
            base_hash=file_hash(SECRET),
        )
        none = await write(client, session["id"], {}, base_hash=file_hash(SECRET))
    assert (two.status_code, code(two)) == (422, "mcp_write_one_file")
    assert (none.status_code, code(none)) == (422, "mcp_write_one_file")
    assert await files_of(client, session["id"]) == FILES


async def test_claude_cannot_change_the_entry_file(client: httpx.AsyncClient) -> None:
    session = await new_session(client, FILES)
    await set_switch(client, True)
    with acting_as_claude():
        sent = await write(
            client,
            session["id"],
            {"outils.py": "x = 9\n"},
            base_hash=file_hash("x = 1\n"),
            entry="outils.py",
        )
    assert sent.status_code == 200
    assert sent.json()["entry"] == session["entry"]  # l'entrée reste celle de la séance


async def test_size_limits_still_apply_to_claude(client: httpx.AsyncClient) -> None:
    session = await new_session(client, FILES)
    await set_switch(client, True)
    with acting_as_claude():
        huge = await write(
            client, session["id"], {"main.py": "x" * 200_001}, base_hash=file_hash(SECRET)
        )
    assert huge.status_code == 422
    assert await files_of(client, session["id"]) == FILES


async def test_a_write_makes_the_proposals_of_that_file_stale(client: httpx.AsyncClient) -> None:
    session = await new_session(client, FILES)
    await set_switch(client, True)
    proposal = {
        "kind": "proposal",
        "content": "Change.",
        "file_path": "main.py",
        "line_start": 1,
        "line_end": 1,
        "replacement": "x = 5",
        "base_hash": file_hash(SECRET),
    }
    note = (await client.post(f"{API}/sessions/{session['id']}/notes", json=proposal)).json()
    with acting_as_claude():
        done = await write(
            client, session["id"], {"main.py": "x = 6\n"}, base_hash=file_hash(SECRET)
        )
    assert done.is_success
    notes = (await client.get(f"{API}/sessions/{session['id']}/notes")).json()
    assert [(n["id"], n["status"]) for n in notes] == [(note["id"], "stale")]


# --- isolation -----------------------------------------------------------------------------


async def test_another_user_gets_404_even_with_a_valid_hash(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    session = await new_session(client, FILES)
    await set_switch(client, True)
    act_as(app, OTHER)
    await set_switch(client, True)
    with acting_as_claude(OTHER):
        gone = await write(
            client, session["id"], {"main.py": "pris = 1\n"}, base_hash=file_hash(SECRET)
        )
    assert (gone.status_code, code(gone)) == (404, "session_not_found")
    act_as(app, USER)
    assert await files_of(client, session["id"]) == FILES


# --- 10.R : les tests de l'exercice sont ceux de January -----------------------------------


async def test_claude_cannot_write_a_test_file_of_the_exercise(client: httpx.AsyncClient) -> None:
    """Réécrire les tests ferait passer la vérification de January sans rien résoudre : refusé
    (403 `mcp_ide_test_file`), pour les fichiers `test_*.py`, `*_test.py` et `conftest.py` d'une
    séance sur exercice ; le code, lui, s'écrit."""
    files = {"main.py": "x = 1\n", "test_main.py": "def test_ok():\n    assert True\n"}
    session = await new_session(client, files, topic="boucles")
    await set_switch(client, True)
    for name in ("test_main.py", "tests/test_autre.py", "main_test.py", "conftest.py"):
        base = file_hash(files.get(name, ""))
        with acting_as_claude():
            refused = await write(client, session["id"], {name: "assert True\n"}, base_hash=base)
        assert (refused.status_code, code(refused)) == (403, "mcp_ide_test_file"), name
    assert await files_of(client, session["id"]) == files  # rien d'écrit
    with acting_as_claude():
        done = await write(
            client, session["id"], {"main.py": "x = 2\n"}, base_hash=file_hash("x = 1\n")
        )
    assert done.status_code == 200, done.text
    mine = await write(client, session["id"], {**files, "test_main.py": "def test_ok(): ...\n"})
    assert mine.status_code == 200  # January, elle, retouche ses tests


async def test_a_free_session_has_no_exercise_tests_to_protect(client: httpx.AsyncClient) -> None:
    session = await new_session(client, FILES)
    await set_switch(client, True)
    with acting_as_claude():
        done = await write(client, session["id"], {"test_x.py": "z = 1\n"}, base_hash=EMPTY_HASH)
    assert done.status_code == 200, done.text
