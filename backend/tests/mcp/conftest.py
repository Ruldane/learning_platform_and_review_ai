"""Fixtures du MCP : l'application en mode local avec un faux registre et un faux envoyeur (le vrai
vient de B2), et un client dont l'hôte est local ; en mode Google, de vrais cookies de session."""

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from app.bootstrap_mcp import install_gate
from app.mcp.tools import McpGate

# Le mode Google et ses navigateurs (cookies de session réels) : fixtures de l'isolation.
from tests.features.auth.conftest import google, google_app  # noqa: F401, F811
from tests.isolation.conftest import google_client_factory  # noqa: F401
from tests.mcp.support import FakeDispatcher, FakeTools, Mcp


@pytest.fixture
def tools() -> FakeTools:
    return FakeTools()


@pytest.fixture
def inner() -> FakeDispatcher:
    return FakeDispatcher()


@pytest.fixture
async def gate(
    client: httpx.AsyncClient, app: FastAPI, tools: FakeTools, inner: FakeDispatcher
) -> McpGate:
    """La porte de l'application, avec le faux registre et le faux envoyeur (limites et journal
    réels)."""
    return install_gate(app, tools, inner)


@pytest.fixture
async def mcp(app: FastAPI, gate: McpGate) -> AsyncIterator[Mcp]:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as http:
        yield Mcp(http)


@pytest.fixture
async def google_gate(google_app: FastAPI, tools: FakeTools, inner: FakeDispatcher) -> McpGate:  # noqa: F811
    return install_gate(google_app, tools, inner)


@pytest.fixture
async def google_mcp(
    google_app: FastAPI,  # noqa: F811
    google_gate: McpGate,
) -> AsyncIterator[Mcp]:
    """Un client sans cookie sur l'application en mode Google (pour présenter un jeton seul)."""
    transport = httpx.ASGITransport(app=google_app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as http:
        yield Mcp(http)
