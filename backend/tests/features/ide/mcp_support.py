"""Matériel des tests de l'IDE sous identité MCP (10.X) : « Claude » appelle les routes comme le
fait l'envoyeur du MCP (l'identité est posée par le contexte, jamais par un en-tête)."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import httpx

from app.core.caller import MCP_IDENTITY, McpIdentity
from tests.features.ide.support import API, USER


@contextmanager
def acting_as_claude(user_id: str = USER, label: str = "Claude Code") -> Iterator[None]:
    """Les requêtes qui suivent passent par le MCP, au nom de `user_id`."""
    token = MCP_IDENTITY.set(McpIdentity(user_id, "t1", label, frozenset({"ide"}), "write"))
    try:
        yield
    finally:
        MCP_IDENTITY.reset(token)


async def set_switch(client: httpx.AsyncClient, on: bool) -> None:
    """January règle l'interrupteur « Claude peut écrire dans mes fichiers » (par l'interface)."""
    prefs = (await client.get(f"{API}/preferences")).json()
    saved = await client.put(f"{API}/preferences", json={**prefs, "mcp_can_write_files": on})
    assert saved.status_code == 200, saved.text


async def write(
    client: httpx.AsyncClient, session_id: str, files: dict[str, str], **body: Any
) -> httpx.Response:
    return await client.put(f"{API}/sessions/{session_id}/files", json={"files": files, **body})
