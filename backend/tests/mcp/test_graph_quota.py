"""M11 : au plus 30 lancements de parcours par utilisatrice et par jour glissant, comptés **à la
source** : là où l'application démarre réellement une session (`SessionRunner.start`), quand
l'appel vient du MCP. Toute route qui lance un parcours est donc comptée, déclarée ou non. Au-delà :
refus `mcp_graph_quota`, en français, sans contenu, et aucune session n'est créée. L'interface de
January n'est jamais limitée."""

import json
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.agents.graphs.registry import GRAPHS
from app.bootstrap_mcp import install_adapter
from app.mcp.base import FeatureMcp, McpAction, McpGraph
from tests.agents.graphs_for_tests import TEST_GRAPHS, Probe
from tests.mcp.adapter_support import call
from tests.mcp.support import API, Mcp
from tests.sessions_support import use_test_runtime


@pytest.fixture(autouse=True)
def probe(monkeypatch: pytest.MonkeyPatch) -> Iterator[Probe]:
    """Avant l'app : son lifespan construit le moteur avec les parcours de test."""
    probe = use_test_runtime(monkeypatch)
    yield probe
    probe.release_b.set()


@pytest.fixture
async def quota_mcp(client: httpx.AsyncClient, app: FastAPI) -> Mcp:
    """Deux façons de lancer : l'outil de graphe (`POST /sessions`, service des sessions) et la
    route d'une feature (`POST /capture`, par le lanceur) ; plafond réduit à 2."""
    app.state.runtime.runner.launch_quota.limit = 2
    features = [
        FeatureMcp("sessions", graphs=(McpGraph("with_topic"),)),
        # Déclarée **sans** `launches` : le plafond ne dépend pas de la déclaration.
        FeatureMcp("capture", actions=(McpAction("POST /capture", 2, "capture_start_capture"),)),
    ]
    models = {name: spec.input_model for name, spec in {**GRAPHS, **TEST_GRAPHS}.items()}
    install_adapter(app, features, models)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as http:
        yield Mcp(http)


def _quota_error(envelope: dict[str, Any]) -> bool:
    error = envelope["data"].get("error") or {}
    return bool(error.get("code") == "mcp_graph_quota")


async def _sessions(mcp: Mcp) -> int:
    return len((await mcp.http.get(f"{API}/sessions")).json())


async def test_graph_tool_is_refused_over_the_limit_and_nothing_starts(quota_mcp: Mcp) -> None:
    token = await quota_mcp.token(("sessions",), "write")
    for _ in range(2):
        envelope, is_error = await call(quota_mcp, token, "graph_with_topic", {"topic": "a"})
        assert not is_error, envelope

    envelope, is_error = await call(quota_mcp, token, "graph_with_topic", {"topic": "SECRET-42"})

    assert is_error and _quota_error(envelope)
    assert "2 lancements de parcours par jour" in envelope["data"]["error"]["message"]
    assert "SECRET-42" not in json.dumps(envelope)
    assert await _sessions(quota_mcp) == 2  # rien n'a été lancé


async def test_a_feature_route_that_launches_a_graph_is_counted_without_a_declaration(
    quota_mcp: Mcp,
) -> None:
    token = await quota_mcp.token(("sessions", "capture"), "write")
    assert not (await call(quota_mcp, token, "capture_start_capture", {"text": "un"}))[1]
    assert not (await call(quota_mcp, token, "graph_with_topic", {"topic": "a"}))[1]  # même compte

    envelope, is_error = await call(quota_mcp, token, "capture_start_capture", {"text": "deux"})

    assert is_error and _quota_error(envelope)
    assert await _sessions(quota_mcp) == 2


async def test_the_application_itself_is_never_limited(quota_mcp: Mcp) -> None:
    token = await quota_mcp.token(("sessions",), "write")
    for _ in range(2):
        await call(quota_mcp, token, "graph_with_topic", {"topic": "a"})
    for _ in range(3):  # l'interface de January lance sans plafond
        response = await quota_mcp.http.post(
            f"{API}/sessions", json={"graph": "with_topic", "input": {"topic": "à la main"}}
        )
        assert response.status_code in (200, 201, 202), response.text
    assert await _sessions(quota_mcp) == 5


async def test_a_launch_refused_before_starting_gives_its_place_back(quota_mcp: Mcp) -> None:
    token = await quota_mcp.token(("sessions",), "write")
    for _ in range(5):  # entrée invalide : refusée avant tout démarrage, rien n'est consommé
        envelope, is_error = await call(quota_mcp, token, "graph_with_topic", {"topic": 12345})
        assert is_error and not _quota_error(envelope)
    assert not (await call(quota_mcp, token, "graph_with_topic", {"topic": "a"}))[1]
    assert not (await call(quota_mcp, token, "graph_with_topic", {"topic": "b"}))[1]
    assert _quota_error((await call(quota_mcp, token, "graph_with_topic", {"topic": "c"}))[0])
