"""Le garde de couverture du MCP (10.D1, P11) : chaque route de `FEATURE_ROUTERS` est déclarée
(action, niveau) ou exclue avec un motif ; chaque graphe de `GRAPHS` de même ; les niveaux suivent
les règles du plan (lecture 1, écriture 2, suppression, envoi, profil maître et effet hors base 3).
Les routes viennent du code réel (`scripts.mcp_levels.iter_routes`), jamais d'une liste écrite."""

import re
from collections import Counter

import pytest

from app.agents.graphs.registry import GRAPHS
from app.features.registry import FEATURE_ROUTERS, MCP_FEATURES
from app.features.settings.mcp import PREFERENCE_FIELDS, PROTECTED_FIELDS
from app.features.settings.schemas import UserSettings
from app.mcp.base import NEVER_EXPOSED_FEATURES, READ_ONLY_POSTS, McpAction, untrusted_paths_valid
from scripts.mcp_levels import RouteInfo, iter_routes, main, render_table

ROUTES = iter_routes(FEATURE_ROUTERS)
KEYS = {route.key for route in ROUTES}
FEATURES = {feature.feature: feature for feature in MCP_FEATURES}
ACTIONS: list[tuple[str, McpAction]] = [
    (feature.feature, action) for feature in MCP_FEATURES for action in feature.actions
]
ACTION_BY_ROUTE = {action.route: action for _, action in ACTIONS}
EXCLUDED = {key: why for feature in MCP_FEATURES for key, why in feature.excluded.items()}

GRAPH_PREFIX = "graph:"
# Écrivent (ou peuvent écrire) au profil maître : niveau 3 et contrôle préalable.
PROFILE_WRITES = frozenset(
    {
        "PUT /profile",
        "POST /projects/{project_id}/profile-entry",
        "PATCH /cv/modifications/{modification_id}",
    }
)
# Effets hors base (vecteurs, fichiers) : déclarés `external`, donc niveau 3.
KNOWN_EXTERNAL = frozenset(
    {
        "POST /memory/items",
        "PATCH /memory/items/{item_id}",
        "DELETE /memory/items/{item_id}",
        "POST /memory/items/{item_id}/merge",
        "POST /memory/reindex",
        "POST /documents/text",
        "DELETE /postings/{posting_id}",
        "POST /programs/{program_id}/validate",
        "PUT /profile",
        "POST /cv/reviews/{review_id}/generate",
        "POST /projects/{project_id}/profile-entry",
    }
)
# Du texte venu du web : la réponse doit le déclarer `untrusted`.
WEB_TEXT_ROUTES = frozenset(
    {
        "POST /postings",
        "GET /postings",
        "GET /postings/{posting_id}",
        "GET /research/sources",
        "GET /resources",
        "GET /radar/runs/{run_id}",
        "GET /radar/latest",
        "GET /memory/items",
        "POST /memory/search",
        "GET /applications/{application_id}",
    }
)
IDE_CODE_WRITES = (
    "POST /ide/notes/{note_id}/accept",
    "POST /ide/notes/{note_id}/reject",
)
SETTINGS_SECRETS = (
    "GET /settings/api-keys",
    "POST /settings/api-keys",
    "DELETE /settings/api-keys/{provider}",
    "POST /settings/api-keys/{provider}/test",
    "GET /settings/models",
    "GET /settings/agents",
)


def _is_route_key(key: str) -> bool:
    return not key.startswith(GRAPH_PREFIX)


def _route(key: str) -> RouteInfo:
    return next(route for route in ROUTES if route.key == key)


def test_routes_are_found() -> None:
    assert len(ROUTES) >= 178  # 147 des phases 1 à 9, plus 18 `ide` et 13 `mcp`
    assert any(route.method == "WS" for route in ROUTES)


def test_every_feature_has_one_manifest() -> None:
    names = [feature.feature for feature in MCP_FEATURES]
    assert len(names) == len(set(names))
    assert set(names) == {route.feature for route in ROUTES}


def test_every_route_declared_or_excluded() -> None:
    missing = [
        route.key
        for route in ROUTES
        if route.key not in ACTION_BY_ROUTE and route.key not in EXCLUDED
    ]
    assert missing == []


def test_no_stale_declaration() -> None:
    declared = [action.route for _, action in ACTIONS]
    assert [key for key, n in Counter(declared).items() if n > 1] == []
    assert [key for key in declared if key not in KEYS] == []
    assert [key for key in EXCLUDED if _is_route_key(key) and key not in KEYS] == []
    assert [key for key in EXCLUDED if key in ACTION_BY_ROUTE] == []
    for feature, action in ACTIONS:
        assert _route(action.route).feature == feature, action.route
    for feature in MCP_FEATURES:
        for key in feature.excluded:
            if _is_route_key(key):
                assert _route(key).feature == feature.feature, key
    declared_graphs = {g.graph for feature in MCP_FEATURES for g in feature.graphs}
    assert declared_graphs <= set(GRAPHS)
    excluded_graphs = {k.removeprefix(GRAPH_PREFIX) for k in EXCLUDED if not _is_route_key(k)}
    assert excluded_graphs <= set(GRAPHS)
    assert not declared_graphs & excluded_graphs


def test_every_graph_declared_or_excluded() -> None:
    declared = {g.graph for feature in MCP_FEATURES for g in feature.graphs}
    excluded = {k.removeprefix(GRAPH_PREFIX) for k in EXCLUDED if not _is_route_key(k)}
    assert sorted(set(GRAPHS) - declared - excluded) == []


def test_excluded_graphs_say_who_launches_them() -> None:
    """Un graphe exclu dit pourquoi : démo interne, ou la route (existante) qui seule le lance."""
    for key, why in EXCLUDED.items():
        if _is_route_key(key):
            continue
        names_a_route = any(route in why for route in KEYS if route != "WS")
        names_a_route = names_a_route or any(
            route.path in why and route.method in why for route in ROUTES
        )
        assert "démo interne" in why or names_a_route, key


def test_read_routes_are_level_1() -> None:
    for _, action in ACTIONS:
        if action.route.startswith("GET "):
            assert action.level == 1, action.route


def test_write_routes_are_level_2_or_3() -> None:
    for _, action in ACTIONS:
        if action.route.startswith("GET ") or action.route in READ_ONLY_POSTS:
            continue
        assert action.level in (2, 3), action.route
    for route in READ_ONLY_POSTS:
        assert ACTION_BY_ROUTE[route].level == 1


def test_delete_routes_are_level_3() -> None:
    deletes = [a for _, a in ACTIONS if a.route.startswith("DELETE ")]
    assert deletes
    assert all(action.level == 3 for action in deletes)


def test_external_effects_are_level_3() -> None:
    for _, action in ACTIONS:
        if action.side_effects == "external":
            assert action.level == 3, action.route
    for route in KNOWN_EXTERNAL:
        assert ACTION_BY_ROUTE[route].side_effects == "external", route
        assert ACTION_BY_ROUTE[route].level == 3, route


def test_never_exposed_features_have_no_action() -> None:
    for name in NEVER_EXPOSED_FEATURES:
        feature = FEATURES[name]
        assert feature.actions == () and feature.graphs == ()
        owned = [route.key for route in ROUTES if route.feature == name]
        assert owned and set(owned) <= set(feature.excluded)


def test_settings_secrets_are_never_declared() -> None:
    for key in SETTINGS_SECRETS:
        assert key in FEATURES["settings"].excluded and key not in ACTION_BY_ROUTE
    names = " ".join(action.name for _, action in ACTIONS)
    assert "api_key" not in names and "models" not in names


def test_settings_put_only_through_the_preferences_action() -> None:
    action = ACTION_BY_ROUTE["PUT /settings"]
    assert action.name == "settings_update_preferences"
    assert action.level == 2
    assert action.merge_from == "GET /settings" and "GET /settings" in ACTION_BY_ROUTE
    assert action.body_fields == PREFERENCE_FIELDS
    assert not PREFERENCE_FIELDS & PROTECTED_FIELDS
    assert {"tiers", "agent_overrides"} == PROTECTED_FIELDS
    # Un champ de plus dans `UserSettings` oblige à décider s'il est sensible.
    assert set(UserSettings.model_fields) == PREFERENCE_FIELDS | PROTECTED_FIELDS


def test_exclusions_have_a_real_reason() -> None:
    assert EXCLUDED
    for key, why in EXCLUDED.items():
        assert len(why) >= 20, key
        assert "todo" not in why.lower() and "fixme" not in why.lower(), key


def test_upload_and_stream_routes_are_excluded() -> None:
    risky = [route for route in ROUTES if route.upload or route.binary]
    assert {route.key for route in risky} >= {
        "POST /documents",
        "POST /profile/import",
        "POST /cv/templates",
        "POST /projects/{project_id}/submit",
        "GET /cv/versions/{version_id}/pdf",
        "WS /sessions/{session_id}/stream",
    }
    for route in risky:
        # Un formulaire sans fichier (`encoding="form"`) peut être déclaré : ses fichiers sont
        # écartés du schéma de l'outil. Tout autre envoi de fichier ou flux est exclu.
        action = ACTION_BY_ROUTE.get(route.key)
        if action is not None:
            assert action.encoding == "form" and route.key not in EXCLUDED, route.key
        else:
            assert route.key in EXCLUDED, route.key


def test_text_variants_of_uploads_are_declared() -> None:
    assert "POST /documents/text" in ACTION_BY_ROUTE
    assert "POST /capture" in ACTION_BY_ROUTE


def test_ide_code_writes_are_excluded() -> None:
    for key in IDE_CODE_WRITES:
        assert key in FEATURES["ide"].excluded and key not in ACTION_BY_ROUTE
    # `PUT files` est l'écriture de Claude (10.X) : niveau 2, un fichier, jamais le fichier d'entrée
    write = ACTION_BY_ROUTE["PUT /ide/sessions/{session_id}/files"]
    assert (write.level, write.name) == (2, "ide_write_file")
    assert write.body_fields == frozenset({"files", "base_hash"})
    assert "PUT /ide/sessions/{session_id}/files" not in FEATURES["ide"].excluded
    # l'interrupteur qui l'autorise ne se règle jamais par le MCP
    assert "PUT /ide/preferences" in FEATURES["ide"].excluded
    assert "PUT /ide/preferences" not in ACTION_BY_ROUTE


def test_profile_write_actions_have_precheck() -> None:
    for key in PROFILE_WRITES:
        action = ACTION_BY_ROUTE[key]
        assert action.level == 3, key
        assert action.precheck is not None, key
    others = [a.route for _, a in ACTIONS if a.precheck and a.route not in PROFILE_WRITES]
    assert others == []


def test_tool_names_unique_valid_and_short() -> None:
    names = [action.name for _, action in ACTIONS]
    assert len(names) == len(set(names))
    for feature, action in ACTIONS:
        assert re.fullmatch(r"[a-z0-9_]{1,64}", action.name), action.name
        assert action.name.startswith(f"{feature}_"), action.name
        assert action.name.count("_") >= 2, action.name  # <feature>_<verbe>_<objet>


def test_untrusted_paths_are_valid_and_web_text_is_fenced() -> None:
    for _, action in ACTIONS:
        assert untrusted_paths_valid(action.untrusted), action.route
    for feature in MCP_FEATURES:
        for graph in feature.graphs:
            assert untrusted_paths_valid(graph.untrusted), graph.graph
    for route in WEB_TEXT_ROUTES:
        assert ACTION_BY_ROUTE[route].untrusted, route


def test_every_action_has_a_summary_and_level_3_says_it_needs_confirmation() -> None:
    for _, action in ACTIONS:
        assert action.summary and len(action.summary) >= 20, action.route
        if action.level == 3:
            assert "confirmer" in action.summary, action.route


def test_levels_table_is_printed_sorted_by_feature(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    printed = capsys.readouterr().out
    assert printed == render_table(MCP_FEATURES) + "\n"
    section = printed.split("\n\n")[0].splitlines()[1:]
    assert len(section) == len(ACTIONS)
    features = [line.split(" | ")[0] for line in section]
    assert features == sorted(features)
    for _, action in ACTIONS:
        assert action.name in printed
