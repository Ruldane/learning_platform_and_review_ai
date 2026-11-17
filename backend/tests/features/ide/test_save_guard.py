"""L'enregistrement de l'interface ne perd jamais l'écriture de Claude (10.X) : `base_hashes` (la
version sur laquelle chaque fichier a été édité) est comparé fichier par fichier ; un fichier changé
sur le serveur depuis donne 409 `stale_base` (noms seulement) et rien n'est écrit."""

import httpx
import pytest
from fastapi import FastAPI

from app.core.caller import Caller
from app.core.errors import AppError
from app.features.ide.service import file_hash, sessions
from app.features.ide.service.context import IdeContext
from tests.features.ide.conftest import USER
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


async def test_a_file_claude_created_is_never_deleted_by_an_old_snapshot(
    client: httpx.AsyncClient,
) -> None:
    session = await new_session(client, FILES)
    await set_switch(client, True)
    with acting_as_claude():
        made = await write(client, session["id"], {"neuf.py": "y = 1\n"}, base_hash=file_hash(""))
    assert made.status_code == 200
    # l'enregistrement automatique repart de l'instantané d'avant : sans `neuf.py`
    refused = await put(client, session["id"], FILES | {"main.py": "a = 2\n"}, hashes(FILES))
    assert (refused.status_code, code(refused)) == (409, "stale_base")
    assert refused.json()["error"]["details"] == {"files": ["neuf.py"]}
    assert (await server_files(client, session["id"]))["neuf.py"] == "y = 1\n"


async def test_two_concurrent_writes_only_one_passes(
    app: FastAPI, client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = await new_session(client, FILES)
    sid = session["id"]
    factory = app.state.session_factory
    async with factory() as db_b:
        ctx_b = IdeContext(db_b, USER, None, Caller("app", "app"))
        stale = await sessions.get(ctx_b, sid)  # B lit la séance...

        async with factory() as db_a:  # ...A écrit et valide entre-temps
            ctx_a = IdeContext(db_a, USER, None, Caller("app", "app"))
            await sessions.save_files(ctx_a, sid, {**FILES, "main.py": "a = 'A'\n"}, None)
            await db_a.commit()

        async def read_before_a(ctx: IdeContext, session_id: str) -> object:
            return stale

        monkeypatch.setattr(sessions, "get", read_before_a)
        with pytest.raises(AppError) as refused:  # ...B écrit sur sa lecture périmée
            await sessions.save_files(ctx_b, sid, {**FILES, "main.py": "a = 'B'\n"}, None)
        assert refused.value.code == "stale_base" and refused.value.status_code == 409
    monkeypatch.undo()
    assert (await server_files(client, sid))["main.py"] == "a = 'A'\n"  # rien de perdu


async def test_two_concurrent_claude_writes_only_one_passes(
    app: FastAPI, client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = await new_session(client, FILES)
    sid = session["id"]
    await set_switch(client, True)
    factory = app.state.session_factory
    claude = Caller("mcp", "Claude Code")
    async with factory() as db_b:
        ctx_b = IdeContext(db_b, USER, None, claude)
        stale = await sessions.get(ctx_b, sid)
        async with factory() as db_a:
            ctx_a = IdeContext(db_a, USER, None, Caller("app", "app"))
            await sessions.save_files(ctx_a, sid, {**FILES, "main.py": "a = 'A'\n"}, None)
            await db_a.commit()

        async def read_before_a(ctx: IdeContext, session_id: str) -> object:
            return stale

        monkeypatch.setattr(sessions, "get", read_before_a)
        with pytest.raises(AppError) as refused:
            await sessions.write_file_as_claude(
                ctx_b, sid, {"main.py": "a = 'B'\n"}, file_hash(FILES["main.py"])
            )
        assert refused.value.code == "stale_base"
    monkeypatch.undo()
    assert (await server_files(client, sid))["main.py"] == "a = 'A'\n"
