"""Outils des tests de la porte du MCP : un faux registre d'outils et un faux envoyeur (B2 livre
les vrais), et un petit client qui parle JSON-RPC sur `/mcp` avec un hôte local."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.caller import McpIdentity
from app.mcp.tools import ToolResult, ToolSpec

API = "/api/v1"
LOCAL = {"Host": "localhost"}
OBJECT = {"type": "object", "properties": {}}


def spec(
    name: str,
    feature: str,
    level: int = 1,
    untrusted: tuple[str, ...] = (),
    bucket: str | None = None,
) -> ToolSpec:
    return ToolSpec(
        name=name,
        feature=feature,
        level=level,  # type: ignore[arg-type]
        description=f"Outil {name}",
        input_schema=OBJECT,
        untrusted=untrusted,
        bucket=bucket,
    )


SPECS = [
    spec("postings_list", "postings", 1),
    spec("postings_add", "postings", 2),
    spec("postings_delete", "postings", 3),
    spec("postings_read_offer", "postings", 1, untrusted=("description", "items[].title")),
    spec("projects_list", "projects", 1),
    spec("ide_run", "ide", 2, bucket="code_run"),
]


class FakeTools:
    """Comme le vrai registre : `list_for` ne rend que ce que l'identité voit, `get` rend tout."""

    def __init__(self, specs: list[ToolSpec] | None = None) -> None:
        self.specs = {item.name: item for item in (specs if specs is not None else SPECS)}

    def list_for(self, identity: McpIdentity) -> list[ToolSpec]:
        return [item for item in self.specs.values() if item.feature in identity.features]

    def get(self, name: str) -> ToolSpec | None:
        return self.specs.get(name)

    def launchers(self) -> frozenset[str]:
        return frozenset(item.name for item in self.specs.values() if item.starts_graph)


@dataclass
class FakeDispatcher:
    """Garde les appels reçus ; rend ce qu'on a réglé, sinon l'écho des arguments."""

    calls: list[tuple[McpIdentity, str, dict[str, Any]]] = field(default_factory=list)
    results: dict[str, ToolResult] = field(default_factory=dict)
    boom: Exception | None = None

    async def call(
        self, identity: McpIdentity, tool: ToolSpec, arguments: dict[str, Any]
    ) -> ToolResult:
        self.calls.append((identity, tool.name, arguments))
        if self.boom is not None:
            raise self.boom
        return self.results.get(
            tool.name, ToolResult(data={"echo": arguments}, ids={"posting_id": "p1"})
        )


def rpc_body(method: str, params: Mapping[str, Any] | None = None, id: Any = 1) -> dict[str, Any]:
    body: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
    if id is not None:
        body["id"] = id
    if params is not None:
        body["params"] = dict(params)
    return body


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@dataclass
class Mcp:
    """Le client de test : crée des jetons par l'API (comme January), parle à `/mcp`."""

    http: httpx.AsyncClient

    async def enable(self, flag: bool = True) -> None:
        response = await self.http.put(f"{API}/mcp/settings", json={"enabled": flag})
        assert response.status_code == 200, response.text

    async def token(
        self,
        features: tuple[str, ...] = ("postings",),
        mode: str = "read",
        *,
        enable: bool = True,
        label: str = "Claude Code",
        days: int = 30,
    ) -> str:
        if enable:
            await self.enable()
        body = {"label": label, "features": list(features), "mode": mode, "expires_in_days": days}
        response = await self.http.post(f"{API}/mcp/tokens", json=body)
        assert response.status_code == 201, response.text
        token: str = response.json()["token"]
        return token

    async def post(
        self,
        token: str | None,
        body: Any,
        headers: Mapping[str, str] | None = None,
        content: bytes | None = None,
    ) -> httpx.Response:
        sent = {**LOCAL, **(bearer(token) if token else {}), **(headers or {})}
        if content is not None:
            return await self.http.post("/mcp", content=content, headers=sent)
        return await self.http.post("/mcp", json=body, headers=sent)

    async def rpc(
        self,
        token: str | None,
        method: str,
        params: Mapping[str, Any] | None = None,
        id: Any = 1,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        return await self.post(token, rpc_body(method, params, id), headers)

    async def call(
        self, token: str, name: str, arguments: Mapping[str, Any] | None = None
    ) -> httpx.Response:
        params = {"name": name, "arguments": dict(arguments or {})}
        return await self.rpc(token, "tools/call", params)
