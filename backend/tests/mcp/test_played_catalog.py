from app.agents.graphs.registry import GRAPHS
from app.features.registry import MCP_FEATURES
from tests.mcp.adapter_support import call
from tests.mcp.support import Mcp


async def test_play_catalog_lists_only_launches_in_token_scope(claude: Mcp) -> None:
    token = await claude.token(("sessions", "ide"), "read")
    result, failed = await call(claude, token, "agents_play_list")
    assert not failed, result
    catalog = {item["launch"]: item for item in result["data"]}
    assert set(catalog) == {"ide_teach_session", "ide_generate_exercise", "graph_demo_debate"}
    assert catalog["ide_teach_session"]["graph"] == "ide_teacher"
    assert "session_id" in catalog["ide_teach_session"]["input_schema"]["properties"]


async def test_play_catalog_matches_declared_launches(claude: Mcp) -> None:
    features = tuple(
        feature.feature
        for feature in MCP_FEATURES
        if feature.actions or feature.graphs or feature.play_actions
    )
    token = await claude.token(features, "read")
    result, failed = await call(claude, token, "agents_play_list")
    assert not failed, result
    direct = {
        graph.graph for feature in MCP_FEATURES for graph in feature.graphs if not graph.follow_only
    }
    via_routes = {
        action.launches
        for feature in MCP_FEATURES
        for action in (*feature.actions, *feature.play_actions)
        if action.level == 2 and action.launches is not None
    }
    followed = {
        graph.graph for feature in MCP_FEATURES for graph in feature.graphs if graph.follow_only
    }
    expected = direct | via_routes
    assert {item["graph"] for item in result["data"]} == expected
    # A graph can be followed without exposing a level 2 launch.
    assert expected | followed == set(GRAPHS)
