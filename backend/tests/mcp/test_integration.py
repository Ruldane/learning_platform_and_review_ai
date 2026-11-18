"""L'intégration de la phase 10 (10.I) : les déclarations des features posées sur le registre réel
de l'application, et les dernières retouches de la relecture de l'adaptateur (R1 à R3, M7)."""

import asyncio
from collections.abc import Iterable, Iterator
from typing import Any

import httpx
import pytest
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.graphs.registry import GRAPHS
from app.bootstrap_mcp import install_adapter
from app.db.models.mcp import McpCall
from app.features.registry import FEATURE_ROUTERS, MCP_FEATURES
from app.features.sessions.service import ROUTE_ONLY
from app.features.settings.mcp import PREFERENCE_FIELDS, PROTECTED_FIELDS
from app.mcp import dispatch
from app.mcp.base import FeatureMcp, McpAction
from app.mcp.registry import Registry, build_registry
from app.mcp.target import _KEYS, label_of, reader_of_target
from tests.mcp.adapter_support import call
from tests.mcp.support import Mcp, spec

API = "/api/v1"
# Des fonctionnalités dont le titre ou la société viennent d'un texte du web (offres, candidatures).
WEB_FED = frozenset({"postings", "applications"})


def _application() -> FastAPI:
    app = FastAPI()
    for router in FEATURE_ROUTERS:
        app.include_router(router, prefix=API)
    return app


@pytest.fixture(scope="module")
def real() -> tuple[FastAPI, Registry]:
    app = _application()
    models = {name: item.input_model for name, item in GRAPHS.items()}
    return app, build_registry(MCP_FEATURES, app, models)


def test_the_real_declarations_build_a_registry(real: tuple[FastAPI, Registry]) -> None:
    assert len(real[1].all()) > 100


def test_preferences_read_only_returns_the_preference_fields(
    real: tuple[FastAPI, Registry],
) -> None:
    tool = real[1].get("settings_get_preferences")
    assert tool is not None and tool.level == 1
    assert tool.response_fields == PREFERENCE_FIELDS
    assert not tool.response_fields & PROTECTED_FIELDS  # jamais `tiers` ni `agent_overrides`


def test_january_gestures_are_excluded_and_not_tools(real: tuple[FastAPI, Registry]) -> None:
    """10.R (I1) : répondre à un quiz, noter une fiche et rendre un projet sont des gestes de
    January, jamais faits à sa place : ni outil, ni action déclarée (motif dans `excluded`)."""
    names = {tool.name for tool in real[1].all()}
    assert {"quiz_submit_attempt", "quiz_review_card", "projects_submit_project"}.isdisjoint(names)
    for feature, route in (
        ("quiz", "POST /quizzes/{quiz_id}/attempts"),
        ("quiz", "POST /flashcards/{card_id}/review"),
        ("projects", "POST /projects/{project_id}/submit"),
    ):
        declared = next(item for item in MCP_FEATURES if item.feature == feature)
        assert "geste de january" in declared.excluded[route].lower(), route
        assert route not in {action.route for action in declared.actions}


def test_route_only_graphs_have_no_launch_tool_only_their_route(
    real: tuple[FastAPI, Registry],
) -> None:
    registry = real[1]
    names = {tool.name for tool in registry.all()}
    for graph in ROUTE_ONLY:
        assert f"graph_{graph}" not in names, graph
    for graph in set(GRAPHS) - set(ROUTE_ONLY) - {"demo_debate"}:
        assert f"graph_{graph}" in names, graph  # les autres se lancent par leur outil de graphe
    # Le suivi garde ses champs non fiables : le résultat d'une session de rendu est entouré.
    assert registry.graph_untrusted["project_review"] == ("result",)


def test_every_launching_route_is_marked_and_every_route_only_graph_follows() -> None:
    """`launches` (affichage des niveaux) nomme un parcours de l'application ; chaque parcours de
    `ROUTE_ONLY` a une route déclarée qui le lance, y compris en mode joué.
    Le plafond (M11) ne dépend pas de ces marques."""
    declared: dict[str, list[str]] = {}
    for feature in MCP_FEATURES:
        for action in (*feature.actions, *feature.play_actions):
            if action.launches is not None:
                assert action.launches in GRAPHS, action.route
                assert action.level == 2, action.route
                assert action.route.startswith("POST ") or action.route == "GET /brief/today"
                declared.setdefault(action.launches, []).append(action.route)
    excluded_graphs = {
        key.removeprefix("graph:")
        for feature in MCP_FEATURES
        for key in feature.excluded
        if key.startswith("graph:")
    }
    assert not set(ROUTE_ONLY) - set(declared) - excluded_graphs
    for feature in MCP_FEATURES:
        for graph in feature.graphs:
            assert graph.follow_only == (graph.graph in ROUTE_ONLY), graph.graph


def test_routes_that_start_a_graph_say_so_for_the_levels_table() -> None:
    """Affichage seulement (le plafond est compté à la source) : ces routes lancent un parcours."""
    wanted = {
        "POST /interviews": "interview",
        "POST /postings/{posting_id}/gap": "gap_analysis",
        "POST /goals": "learning_council",
        "POST /goals/{goal_id}/council": "learning_council",
        "POST /documents/{document_id}/learned": "learned_document",
    }
    found = {
        action.route: action.launches for feature in MCP_FEATURES for action in feature.actions
    }
    assert {route: found.get(route) for route in wanted} == wanted


def _api_routes(routes: Iterable[Any]) -> Iterator[APIRoute]:
    """Toutes les `APIRoute`, sous-routeurs (`include_router`) et montages compris."""
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
        elif (nested := getattr(route, "original_router", None)) is not None:
            yield from _api_routes(nested.routes)
        elif (nested_routes := getattr(route, "routes", None)) is not None:
            yield from _api_routes(nested_routes)


def test_no_route_of_the_application_is_hidden_from_the_schema(app: FastAPI) -> None:
    """R2 : l'index des routes du MCP vient de l'OpenAPI ; une route cachée y échapperait. Le
    parcours entre dans les sous-routeurs et les montages (sinon il ne verrait rien)."""
    for application in (_application(), app):
        seen = list(_api_routes(application.routes))
        assert len(seen) > 150  # le parcours voit bien les routes des features
        hidden = [route.path for route in seen if not route.include_in_schema]
        assert hidden == []


def test_every_settings_action_filters_the_response(real: tuple[FastAPI, Registry]) -> None:
    """I2 : lecture ou écriture, une action sur `/settings` ne rend que les préférences, jamais les
    modèles par niveau ni les surcharges par agent."""
    settings = [
        tool
        for tool in real[1].all()
        if tool.route is not None and tool.route[1].startswith("/settings")
    ]
    assert {tool.name for tool in settings} >= {
        "settings_get_preferences",
        "settings_update_preferences",
    }
    for tool in settings:
        assert tool.response_fields is not None, tool.name
        assert not tool.response_fields & PROTECTED_FIELDS, tool.name


def _response_keys(app: FastAPI, route: tuple[str, str]) -> list[str]:
    schema = app.openapi()
    method, path = route
    operation = schema["paths"][API + path][method.lower()]
    ok = operation["responses"].get("200") or operation["responses"]["202"]
    body = ok["content"]["application/json"]["schema"]
    if "$ref" in body:
        body = schema["components"]["schemas"][body["$ref"].rsplit("/", 1)[-1]]
    return list(body.get("properties", {}))


def test_reads_that_name_a_target_declare_web_text_untrusted(
    real: tuple[FastAPI, Registry],
) -> None:
    """R3 : le libellé d'une demande « À confirmer » est lu par la route GET de la ressource ; si
    la société ou le titre viennent du web, la lecture les déclare `untrusted`."""
    app, registry = real
    checked = 0
    for tool in registry.all():
        if tool.level == 1 or tool.route is None:
            continue
        found = reader_of_target(registry, tool, tool.route[1])
        if found is None or found[0].feature not in WEB_FED:
            continue
        reader = found[0]
        assert reader.route is not None
        for key in set(_response_keys(app, reader.route)) & set(_KEYS):
            assert key in reader.untrusted, (tool.name, reader.name, key)
            checked += 1
    assert checked >= 4  # offres et candidatures : société et titre


def test_label_masks_keys_before_cutting_them() -> None:
    """R1 : une clé coupée par la limite du libellé ne laisse jamais un préfixe lisible."""
    secret = "sk-ant-api03-" + "A" * 40
    title = "x" * 69 + " " + secret  # la coupe à 80 caractères tomberait au milieu de la clé
    label = label_of({"title": title}, spec("postings_get", "postings", 1))
    assert label is not None
    assert "sk-ant" not in label and "AAAA" not in label


# --- M7 : un délai dépassé sur une écriture ---


def _slow_router() -> APIRouter:
    router = APIRouter(prefix="/_slow")

    @router.post("/write")
    async def write() -> dict[str, str]:
        await asyncio.sleep(1)
        return {"ok": "oui"}

    return router


async def test_a_timeout_on_a_write_says_it_may_have_been_applied(
    client: httpx.AsyncClient,
    app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    app.include_router(_slow_router(), prefix=API)
    app.openapi_schema = None
    monkeypatch.setattr(dispatch, "REQUEST_TIMEOUT_S", 0.05)
    models = {name: item.input_model for name, item in GRAPHS.items()}
    slow = FeatureMcp("slow", actions=(McpAction("POST /_slow/write", 2, "slow_write"),))
    install_adapter(app, [slow], models)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as http:
        mcp = Mcp(http)
        token = await mcp.token(("slow",), "write")
        envelope, is_error = await call(mcp, token, "slow_write")

    assert is_error
    assert envelope["data"]["error"]["code"] == "tool_timeout"
    assert "a pu écrire" in envelope["notice"] and "vérifie" in envelope["notice"]
    async with db_session_factory() as db:
        row = (await db.execute(select(McpCall).where(McpCall.action == "slow_write"))).scalar_one()
    assert row.code == 504 and row.ids == {"outcome": "timeout"}
