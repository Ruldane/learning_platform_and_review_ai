"""Registre, arguments et limiteur après la relecture 10.B2 : tables enregistrables (M2), refus au
démarrage (M3), route sœur (M4), fenêtre du limiteur (M5), garde des routes de réglages (M9 de
10.B1)."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import Column, MetaData, String, Table
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.accounts import AuthSession
from app.features.registry import MCP_FEATURES
from app.mcp.arguments import ArgumentError, build_request
from app.mcp.base import FeatureMcp, McpAction
from app.mcp.limits import Limits, RateLimiter
from app.mcp.registry import _check_action, build_registry
from app.mcp.rowstate import recordable
from app.mcp.schema import API_PREFIX, McpConfigError, RoutePlan, never_reachable
from tests.mcp.adapter_support import call
from tests.mcp.support import API, Mcp

Factory = async_sessionmaker[AsyncSession]


def one(*actions: McpAction) -> list[FeatureMcp]:
    return [FeatureMcp("applications", actions=actions)]


# --- M2 : recordable --------------------------------------------------------------------------


def test_recordable_respects_table_info_and_auth_sessions() -> None:
    secret = Table(
        "secrets", MetaData(), Column("id", String, primary_key=True), info={"export": False}
    )
    plain = Table("plain", MetaData(), Column("id", String, primary_key=True))

    assert not recordable(secret)
    assert not recordable(AuthSession.__table__)  # type: ignore[arg-type]
    assert recordable(plain)


# --- M3 : le registre refuse au démarrage -----------------------------------------------------


@pytest.mark.parametrize(
    ("action", "message"),
    [
        (McpAction("DELETE /applications/{application_id}", 2, "x"), "suppression"),
        (McpAction("POST /sessions", 2, "x"), "sessions"),
        (McpAction("GET /applications", 1, "x", precheck=lambda asked: None), "contrôle"),  # type: ignore[arg-type,return-value]
        (
            McpAction("PATCH /applications/{application_id}", 2, "x", precheck=lambda a: None),
            "contrôle",
        ),  # type: ignore[arg-type,return-value]
    ],
)
def test_registry_refuses_what_the_doc_forbids(
    app: FastAPI, action: McpAction, message: str
) -> None:
    with pytest.raises(McpConfigError, match=message):
        build_registry(one(action), app)


def test_registry_requires_fields_under_every_settings_route() -> None:
    for route, level in (("GET /settings/extra", 1), ("PUT /settings/extra", 2)):
        with pytest.raises(McpConfigError, match="réglages"):
            _check_action("settings", McpAction(route, level, "extra"))  # type: ignore[arg-type]
    _check_action(
        "settings", McpAction("GET /settings/extra", 1, "extra", response_fields=frozenset({"a"}))
    )


def test_registry_requires_response_fields_for_every_settings_method() -> None:
    """10.R (M6) : une écriture sous `/settings` rend l'objet entier : sans `response_fields`, les
    modèles et surcharges par agent (niveau 4) sortiraient ; avec eux, jamais `tiers` ni
    `agent_overrides`."""
    body = frozenset({"timezone"})
    with pytest.raises(McpConfigError, match="response_fields"):
        _check_action("settings", McpAction("PUT /settings", 2, "p", body_fields=body))  # type: ignore[arg-type]
    for leak in ("tiers", "agent_overrides"):
        with pytest.raises(McpConfigError, match=leak):
            _check_action(
                "settings",
                McpAction(
                    "PUT /settings", 2, "p", body_fields=body, response_fields=frozenset({leak})
                ),  # type: ignore[arg-type]
            )
        with pytest.raises(McpConfigError, match=leak):
            _check_action(
                "settings",
                McpAction("GET /settings", 1, "g", response_fields=frozenset({"timezone", leak})),
            )
    _check_action(
        "settings",
        McpAction("PUT /settings", 2, "p", body_fields=body, response_fields=body),
    )


# --- M9 de 10.B1 : garde des routes de réglages et de compte ------------------------------------

SECRET_PREFIXES = ("/settings", "/auth", "/account", "/mcp")
# Les seules routes de ces préfixes qui ne sont pas de niveau 4 : les préférences, jamais sans
# `response_fields` (lecture) ou `body_fields` (écriture) si on les déclare.
PREFERENCE_ROUTES = frozenset({"GET /settings", "PUT /settings"})


def unprotected(routes: list[tuple[str, str]], declared: dict[str, McpAction]) -> list[str]:
    """Les routes sous un préfixe sensible qui ne sont ni bloquées sous une identité MCP
    (`never_reachable`) ni des préférences déclarées avec leurs champs."""
    bad: list[str] = []
    for method, path in routes:
        if not any(path == p or path.startswith(p + "/") for p in SECRET_PREFIXES):
            continue
        key = f"{method} {path}"
        if never_reachable(path, method):
            continue
        action = declared.get(key)
        if key == "GET /account/export" and action and action.artifact and action.level == 1:
            continue
        if key == "POST /account/delete" and action and action.level == 3:
            continue
        complete = action is None or (
            action.response_fields is not None and (method == "GET" or action.body_fields)
        )  # fmt: skip
        if key in PREFERENCE_ROUTES and complete:
            continue
        bad.append(key)
    return bad


def test_every_secret_route_is_blocked_or_declared_with_fields(app: FastAPI) -> None:
    routes = [
        (method.upper(), path.removeprefix(API_PREFIX))
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    ]
    declared = {action.route: action for item in MCP_FEATURES for action in item.actions}

    assert unprotected(routes, declared) == []
    assert ("GET", "/settings") in routes  # la liste n'est pas vide


def test_the_secret_route_guard_catches_an_open_route() -> None:
    loose = McpAction("PUT /settings", 2, "loose")
    assert unprotected([("GET", "/settings/secret")], {}) == ["GET /settings/secret"]
    assert unprotected([("PUT", "/settings")], {"PUT /settings": loose}) == ["PUT /settings"]
    assert unprotected([("GET", "/settings/api-keys"), ("GET", "/postings")], {}) == []


# --- M4 : un paramètre de chemin ne désigne pas une route sœur -------------------------------


async def test_path_parameter_cannot_reach_a_static_sibling_route(
    amcp: Mcp, writer: str, client: httpx.AsyncClient
) -> None:
    assert (await client.get(f"{API}/applications/stats")).status_code == 200  # elle existe

    envelope, is_error = await call(amcp, writer, "applications_get", {"application_id": "stats"})

    assert is_error and envelope["data"]["error"]["code"] == "invalid_arguments"
    assert "route" in envelope["data"]["error"]["message"]
    listed = await call(amcp, writer, "applications_get", {"application_id": "inconnue"})
    assert listed[1] and listed[0]["data"]["error"]["code"] == "application_not_found"


def test_path_parameter_rejects_braces_and_substitutes_once() -> None:
    plan = RoutePlan(
        "GET", "/a/{x}/b/{y}", frozenset({"x", "y"}), frozenset(), {}, None, False, False
    )

    with pytest.raises(ArgumentError):
        build_request(plan, {"x": "{y}", "y": "v"})
    built = build_request(plan, {"y": "2", "x": "1"})
    assert built.path == "/a/1/b/2"


# --- M5 : le plafond de requêtes ne garde pas un jour d'instants ------------------------------


async def test_request_window_forgets_instants_outside_its_own_window() -> None:
    limiter = RateLimiter(Limits(requests_per_minute=600))
    start = datetime.now(UTC)
    for index in range(300):
        await limiter.check_request("t1", start + timedelta(milliseconds=index))
    later = start + timedelta(minutes=3)
    await limiter.check_request("t1", later)

    kept = [len(events) for key, events in limiter._events.items() if key[1] == "requests"]
    assert kept == [1]
