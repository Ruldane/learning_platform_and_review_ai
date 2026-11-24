"""Le registre des outils (10.B2) : le schéma tiré de l'OpenAPI et tout ce qui fait échouer le
démarrage (route absente, niveau 4, effet externe, niveau 1 qui écrit, nom en double)."""

from typing import Any

import pytest
from fastapi import FastAPI

from app.core.caller import McpIdentity
from app.mcp.base import FeatureMcp, McpAction, McpGraph
from app.mcp.registry import build_registry
from app.mcp.schema import McpConfigError, build_route_tool
from tests.agents.graphs_for_tests import TopicInput
from tests.mcp.adapter_support import add_probe, declarations
from tests.mcp.support import Mcp


def one(feature: str, *actions: McpAction) -> list[FeatureMcp]:
    return [FeatureMcp(feature, actions=actions)]


def test_schema_merges_path_query_and_body(app: FastAPI) -> None:
    add_probe(app)
    registry = build_registry(declarations(), app, {"with_topic": TopicInput})
    update = registry.get("applications_update")
    listing = registry.get("applications_list")
    assert update is not None and listing is not None

    props = update.input_schema["properties"]
    assert "application_id" in props and "company" in props and "title" in props  # chemin + corps
    assert update.input_schema["required"] == ["application_id"]
    assert update.input_schema["additionalProperties"] is False
    assert {"status", "posting_id"} <= listing.input_schema["properties"].keys()  # requête
    assert update.route == ("PATCH", "/applications/{application_id}") and update.level == 2
    assert "Reversible write" in update.description
    event = registry.get("applications_event")
    assert event is not None and "To confirm" in event.description
    # `$ref` des composants devenus `$defs` locaux, jamais de `#/components`.
    assert "#/components" not in str(update.input_schema)
    assert "$defs" in update.input_schema


def test_schema_prefixes_colliding_body_fields() -> None:
    openapi: dict[str, Any] = {
        "paths": {
            "/api/v1/things/{id}": {
                "put": {
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {}}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"id": {"type": "string"}, "name": {}},
                                    "required": ["id"],
                                }
                            }
                        },
                    },
                }
            }
        }
    }
    schema, plan, _ = build_route_tool(
        openapi, "PUT /things/{id}", body_fields=None, merge_from=None, encoding="json"
    )
    assert set(schema["properties"]) == {"id", "body_id", "name"}
    assert plan.body_args == {"body_id": "id", "name": "name"}
    assert schema["required"] == ["id", "body_id"]


def test_registry_fails_on_unknown_route(app: FastAPI) -> None:
    with pytest.raises(McpConfigError, match="missing from the app"):
        build_registry(one("x", McpAction("GET /nope", 1, "x_nope")), app)
    with pytest.raises(McpConfigError, match="malformed route"):
        build_registry(one("x", McpAction("FETCH /applications", 1, "x_bad")), app)
    with pytest.raises(McpConfigError, match="graph declared but unknown"):
        build_registry([FeatureMcp("x", graphs=(McpGraph("inconnu"),))], app, {})


def test_external_side_effect_action_cannot_be_level_2(app: FastAPI) -> None:
    with pytest.raises(ValueError, match="external side effect is level 3"):
        McpAction("POST /memory/items", 2, "memory_add", side_effects="external")
    level_3 = McpAction("POST /memory/items", 3, "memory_add", side_effects="external")
    registry = build_registry(one("memory", level_3), app)
    tool = registry.get("memory_add")
    assert tool is not None and tool.level == 3 and tool.side_effects == "external"


@pytest.mark.parametrize(
    ("feature", "action", "message"),
    [
        ("auth", McpAction("GET /health", 1, "auth_health"), "never exposes a tool"),
        ("x", McpAction("GET /auth/me", 1, "x_me"), "level 4"),
        ("x", McpAction("GET /mcp/settings", 1, "x_mcp"), "level 4"),
        ("x", McpAction("GET /account/credentials", 1, "x_export"), "level 4"),
        ("x", McpAction("GET /settings/api-keys", 1, "x_keys"), "level 4"),
        ("x", McpAction("GET /settings/models", 1, "x_models"), "level 4"),
        ("x", McpAction("GET /settings/agents", 1, "x_agents"), "level 4"),
        ("x", McpAction("PUT /settings", 2, "x_put"), "body_fields"),
        ("x", McpAction("GET /settings", 1, "x_get"), "response_fields"),
        ("x", McpAction("POST /applications", 1, "x_add"), "cannot be level 1"),
        ("x", McpAction("GET /health", 1, "Invalid Name"), "invalid tool name"),
        ("x", McpAction("POST /documents", 2, "x_upload"), "JSON"),
    ],
)
def test_declarations_that_do_not_fit_stop_the_startup(
    app: FastAPI, feature: str, action: McpAction, message: str
) -> None:
    with pytest.raises(McpConfigError, match=message):
        build_registry(one(feature, action), app)


def test_duplicate_tool_names_stop_the_startup(app: FastAPI) -> None:
    twice = one(
        "x", McpAction("GET /health", 1, "x_same"), McpAction("GET /applications", 1, "x_same")
    )
    with pytest.raises(McpConfigError, match="duplicate tool name"):
        build_registry(twice, app)


def test_body_fields_must_exist(app: FastAPI) -> None:
    bad = McpAction(
        "PUT /settings",
        2,
        "x_prefs",
        body_fields=frozenset({"nope"}),
        merge_from="GET /settings",
        response_fields=frozenset({"timezone"}),
    )
    with pytest.raises(McpConfigError, match="unknown body fields"):
        build_registry(one("settings", bad), app)


def test_registry_lists_only_the_scope_but_knows_every_tool(app: FastAPI) -> None:
    add_probe(app)
    registry = build_registry(declarations(), app, {"with_topic": TopicInput})
    identity = McpIdentity("u", "t", "Claude", frozenset({"applications"}), "write")

    listed = {tool.name for tool in registry.list_for(identity)}

    assert "applications_list" in listed and "settings_get" not in listed
    assert registry.get("settings_get") is not None  # connu : refusé en 403, pas « inconnu »
    assert registry.get("graph_with_topic") is not None
    assert registry.get("nope") is None


async def test_tables_of_tools_are_served_to_the_interface(amcp: Mcp) -> None:
    http = amcp.http
    actions = (await http.get("/api/v1/mcp/actions")).json()
    features = (await http.get("/api/v1/mcp/features")).json()

    by_name = {action["name"]: action for action in actions}
    assert by_name["applications_event"]["level"] == 3
    assert by_name["applications_add"]["route"] == "POST /applications"
    assert by_name["graph_with_topic"]["kind"] == "graph"
    assert by_name["graph_with_topic"]["route"] is None
    applications = next(item for item in features if item["feature"] == "applications")
    assert applications == {
        "feature": "applications",
        "read_actions": 2,
        "write_actions": 2,
        "confirm_actions": 1,
    }
