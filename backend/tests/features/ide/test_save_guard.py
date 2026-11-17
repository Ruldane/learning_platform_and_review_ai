"""L'enregistrement de l'interface ne perd jamais l'écriture de Claude (10.X) : `base_hashes` (la
version sur laquelle chaque fichier a été édité) est comparé fichier par fichier ; un fichier changé
sur le serveur depuis donne 409 `stale_base` (noms seulement) et rien n'est écrit."""

import httpx
import pytest

from app.features.ide.service import file_hash
from tests.features.ide.mcp_support import acting_as_claude, set_switch, write
from tests.features.ide.support import API, code, new_session

pytestmark = pytest.mark.usefixtures("me")

FILES = {"main.py": "a = 1\n", "outils.py": "b = 1\n"}


def hashes(files: dict[str, str]) -> dict[str, str]:
    return {name: file_hash(text) for name, text in files.items()}


async def claude_writes(client: httpx.AsyncClient, sid: str, name: str, text: str) -> None:
    await set_switch(client, True)
    with acting_as_claude():
        done = await write(client, sid, {name: text}, base_hash=file_hash(FILES[name]))
    assert done.status_code == 200, done.text


async def put(
    client: httpx.AsyncClient, sid: str, files: dict[str, str], base: dict[str, str] | None
) -> httpx.Response:
    body: dict[str, object] = {"files": files}
    if base is not None:
        body["base_hashes"] = base
    return await client.put(f"{API}/sessions/{sid}/files", json=body)


async def server_files(client: httpx.AsyncClient, sid: str) -> dict[str, str]:
    files: dict[str, str] = (await client.get(f"{API}/sessions/{sid}")).json()["files"]
    return files


async def test_matching_hashes_are_saved(client: httpx.AsyncClient) -> None:
    session = await new_session(client, FILES)
    new = {"main.py": "a = 2\n", "outils.py": "b = 1\n"}
    done = await put(client, session["id"], new, session["file_hashes"])
    assert done.status_code == 200 and done.json()["files"] == new


async def test_a_file_claude_changed_is_409_and_nothing_is_written(
    client: httpx.AsyncClient,
) -> None:
    session = await new_session(client, FILES)
    await claude_writes(client, session["id"], "main.py", "a = 99\n")
    refused = await put(
        client,
        session["id"],
        {"main.py": "a = 2\n", "outils.py": "b = 2\n"},
        hashes(FILES),
    )
    assert (refused.status_code, code(refused)) == (409, "stale_base")
    assert refused.json()["error"]["details"] == {"files": ["main.py"]}
    assert "a = 99" not in refused.text and "a = 2" not in refused.text  # noms seulement
    assert await server_files(client, session["id"]) == {**FILES, "main.py": "a = 99\n"}


async def test_a_file_you_did_not_touch_is_not_reverted(client: httpx.AsyncClient) -> None:
    session = await new_session(client, FILES)
    await claude_writes(client, session["id"], "outils.py", "b = 99\n")
    refused = await put(client, session["id"], FILES | {"main.py": "a = 2\n"}, hashes(FILES))
    assert refused.status_code == 409
    assert refused.json()["error"]["details"] == {"files": ["outils.py"]}
    assert (await server_files(client, session["id"]))["outils.py"] == "b = 99\n"


async def test_sending_the_current_text_is_not_a_conflict(client: httpx.AsyncClient) -> None:
    session = await new_session(client, FILES)
    await claude_writes(client, session["id"], "outils.py", "b = 99\n")
    now = {
        "main.py": "a = 2\n",
        "outils.py": "b = 99\n",
    }  # la page a déjà relu la version de Claude
    done = await put(client, session["id"], now, hashes(FILES))
    assert done.status_code == 200 and done.json()["files"] == now


async def test_without_base_hashes_the_save_still_replaces_everything(
    client: httpx.AsyncClient,
) -> None:
    session = await new_session(client, FILES)
    await claude_writes(client, session["id"], "main.py", "a = 99\n")
    done = await put(client, session["id"], {"main.py": "a = 2\n"}, None)
    assert done.status_code == 200 and done.json()["files"] == {"main.py": "a = 2\n"}


async def test_malformed_hashes_are_422(client: httpx.AsyncClient) -> None:
    session = await new_session(client, FILES)
    bad = await put(client, session["id"], FILES, {"main.py": "abc"})
    assert bad.status_code == 422
