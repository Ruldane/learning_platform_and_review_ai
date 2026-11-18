"""10.X : Claude écrit dans les fichiers de l'IDE par le MCP (`ide_write_file`, niveau 2), sous
l'interrupteur de January ; l'écriture s'annule depuis « Accès MCP » ; l'interrupteur, lui, ne se
règle jamais par le MCP."""

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from app.db.models.ide import IdeSession
from app.features.ide.service import file_hash
from app.mcp.rowstate import recordable
from tests.mcp.adapter_support import read
from tests.mcp.support import API, Mcp


@pytest.fixture
async def client(
    app: FastAPI,
    client: httpx.AsyncClient,  # noqa: F811
) -> AsyncIterator[httpx.AsyncClient]:
    """Le client de ce module : l'hôte est local (la page « Accès MCP » et `/mcp` ne répondent que
    là) ; le client de base a démarré l'application."""
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as http:
        yield http


BEFORE = "print('avant')\n"
SESSION = f"{API}/ide/sessions"


async def make_session(client: httpx.AsyncClient) -> str:
    opened = await client.post(SESSION, json={})
    assert opened.status_code == 201, opened.text
    sid: str = opened.json()["id"]
    saved = await client.put(f"{SESSION}/{sid}/files", json={"files": {"main.py": BEFORE}})
    assert saved.status_code == 200, saved.text
    return sid


async def tool(mcp: Mcp, token: str, name: str, **arguments: object) -> tuple[dict, bool]:  # type: ignore[type-arg]
    return read(await mcp.call(token, name, dict(arguments)))


async def switch(client: httpx.AsyncClient, on: bool) -> None:
    prefs = (await client.get(f"{API}/ide/preferences")).json()
    done = await client.put(f"{API}/ide/preferences", json={**prefs, "mcp_can_write_files": on})
    assert done.status_code == 200, done.text


async def files(client: httpx.AsyncClient, sid: str) -> dict[str, str]:
    got: dict[str, str] = (await client.get(f"{SESSION}/{sid}")).json()["files"]
    return got


async def test_the_files_table_is_recordable() -> None:
    """Condition de l'annulation (P14) : la table des séances a une clé simple et aucun secret."""
    assert recordable(IdeSession.__table__)  # type: ignore[arg-type]


async def test_the_new_tools_are_declared_with_their_levels(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    tools = {t.name: t for t in app.state.mcp_registry.all() if t.feature == "ide"}
    assert tools["ide_write_file"].level == 2 and tools["ide_list_runs"].level == 1
    assert not any("preferences" in t.name and t.level > 1 for t in tools.values())
    assert "ide_save_preferences" not in tools and "ide_put_preferences" not in tools


async def test_write_tool_is_refused_when_the_switch_is_off(client: httpx.AsyncClient) -> None:
    mcp = Mcp(client)
    sid = await make_session(client)
    token = await mcp.token(("ide",), "write")

    envelope, is_error = await tool(
        mcp, token, "ide_write_file", session_id=sid, files={"main.py": "pris\n"},
        base_hash=file_hash(BEFORE),
    )  # fmt: skip

    assert is_error and envelope["data"]["error"]["code"] == "mcp_ide_write_off"
    assert await files(client, sid) == {"main.py": BEFORE}
    assert (await client.get(f"{API}/mcp/changes")).json() == []  # rien à annuler


async def test_write_tool_then_undo_restores_the_previous_content(
    client: httpx.AsyncClient,
) -> None:
    mcp = Mcp(client)
    sid = await make_session(client)
    token = await mcp.token(("ide",), "write")
    await switch(client, True)

    envelope, is_error = await tool(
        mcp, token, "ide_write_file", session_id=sid, files={"main.py": "print('apres')\n"},
        base_hash=file_hash(BEFORE),
    )  # fmt: skip

    assert not is_error, envelope
    assert await files(client, sid) == {"main.py": "print('apres')\n"}
    changes = (await client.get(f"{API}/mcp/changes")).json()
    assert [c["action"] for c in changes] == ["ide_write_file"]
    assert "ide_sessions" in changes[0]["tables"]
    undone = await client.post(f"{API}/mcp/changes/{changes[0]['call_id']}/undo")
    assert undone.status_code == 200, undone.text
    assert await files(client, sid) == {"main.py": BEFORE}


async def test_undo_is_refused_when_january_typed_since(client: httpx.AsyncClient) -> None:
    mcp = Mcp(client)
    sid = await make_session(client)
    token = await mcp.token(("ide",), "write")
    await switch(client, True)
    await tool(
        mcp, token, "ide_write_file", session_id=sid, files={"main.py": "claude\n"},
        base_hash=file_hash(BEFORE),
    )  # fmt: skip
    await client.put(
        f"{SESSION}/{sid}/files", json={"files": {"main.py": "la frappe de January\n"}}
    )
    call_id = (await client.get(f"{API}/mcp/changes")).json()[0]["call_id"]

    refused = await client.post(f"{API}/mcp/changes/{call_id}/undo")

    assert refused.status_code == 409
    assert await files(client, sid) == {"main.py": "la frappe de January\n"}  # sa frappe est gardée


async def test_stale_hash_through_the_tool_is_a_readable_409(client: httpx.AsyncClient) -> None:
    mcp = Mcp(client)
    sid = await make_session(client)
    token = await mcp.token(("ide",), "write")
    await switch(client, True)
    envelope, is_error = await tool(
        mcp, token, "ide_write_file", session_id=sid, files={"main.py": "x\n"},
        base_hash=file_hash("autre chose\n"),
    )  # fmt: skip
    assert is_error and envelope["data"]["error"]["code"] == "stale_base"
    assert await files(client, sid) == {"main.py": BEFORE}


async def test_the_switch_cannot_be_set_through_the_mcp(client: httpx.AsyncClient) -> None:
    mcp = Mcp(client)
    token = await mcp.token(("ide",), "write")
    listed = (await mcp.rpc(token, "tools/list")).json()["result"]["tools"]
    names = {t["name"] for t in listed}
    assert {"ide_write_file", "ide_list_runs", "ide_get_preferences"} <= names
    assert not {n for n in names if "preferences" in n} - {"ide_get_preferences"}
    for guess in ("ide_save_preferences", "ide_put_preferences", "ide_set_preferences"):
        refused = (await mcp.call(token, guess, {"mcp_can_write_files": True})).json()
        assert refused["error"]["code"] == -32602  # outil inconnu : rien ne le déclare
    assert (await client.get(f"{API}/ide/preferences")).json()["mcp_can_write_files"] is False
    # le jeton lit l'interrupteur (pour savoir s'il peut écrire), sans pouvoir le changer
    prefs, _ = await tool(mcp, token, "ide_get_preferences")
    assert prefs["data"]["mcp_can_write_files"] is False


async def test_runs_list_tool_reads_the_runs_of_a_session(client: httpx.AsyncClient) -> None:
    mcp = Mcp(client)
    sid = await make_session(client)
    token = await mcp.token(("ide",), "read")
    envelope, is_error = await tool(mcp, token, "ide_list_runs", session_id=sid)
    assert not is_error and envelope["data"] == []


async def test_undo_moves_files_version_forward(client: httpx.AsyncClient, app: FastAPI) -> None:
    """10.R (M2) : l'annulation ne ramène pas le compteur d'écritures en arrière : une écriture
    lue avant l'annulation reste en conflit (elle comparerait sinon un compteur revenu à son
    ancienne valeur)."""
    mcp = Mcp(client)
    sid = await make_session(client)
    token = await mcp.token(("ide",), "write")
    await switch(client, True)

    async def version() -> int:
        async with app.state.session_factory() as db:
            row = await db.get(IdeSession, sid)
            assert row is not None
            return int(row.files_version)

    await tool(
        mcp, token, "ide_write_file", session_id=sid, files={"main.py": "claude\n"},
        base_hash=file_hash(BEFORE),
    )  # fmt: skip
    written = await version()
    call_id = (await client.get(f"{API}/mcp/changes")).json()[0]["call_id"]
    undone = await client.post(f"{API}/mcp/changes/{call_id}/undo")
    assert undone.status_code == 200, undone.text
    assert await files(client, sid) == {"main.py": BEFORE}
    assert await version() > written
