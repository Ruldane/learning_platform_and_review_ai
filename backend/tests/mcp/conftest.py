"""Fixtures du MCP : l'application en mode local avec un faux registre et un faux envoyeur (le vrai
vient de B2), et un client dont l'hôte est local ; en mode Google, de vrais cookies de session."""

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from app.agents.graphs.registry import GRAPHS
from app.bootstrap_mcp import install_adapter, install_gate
from app.mcp.registry import Registry
from app.mcp.tools import McpGate
from tests.agents.graphs_for_tests import TEST_GRAPHS

# Le mode Google et ses navigateurs (cookies de session réels) : fixtures de l'isolation.
from tests.features.auth.conftest import google, google_app  # noqa: F401, F811
from tests.isolation.conftest import google_client_factory  # noqa: F401
from tests.mcp.adapter_support import FEATURES, add_probe, declarations
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


# --- L'adaptateur réel (10.B2) : registre, envoyeur et demandes sur de vraies routes ---


@pytest.fixture
async def adapter(client: httpx.AsyncClient, app: FastAPI) -> Registry:
    """Le registre réel des déclarations de test (candidatures, réglages, sessions, sonde), avec les
    vraies limites ; `client` a démarré l'application (lifespan)."""
    add_probe(app)
    models = {name: spec.input_model for name, spec in {**GRAPHS, **TEST_GRAPHS}.items()}
    return install_adapter(app, declarations(), models)


@pytest.fixture
async def amcp(app: FastAPI, adapter: Registry) -> AsyncIterator[Mcp]:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as http:
        yield Mcp(http)


@pytest.fixture
async def writer(amcp: Mcp) -> str:
    """Un jeton en écriture sur toutes les features de test."""
    return await amcp.token(FEATURES, "write")
