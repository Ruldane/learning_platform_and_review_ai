from fastapi import FastAPI

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


async def test_all_graphs_have_a_played_launch(claude: Mcp, app: FastAPI) -> None:
    # La session issue d'un choix dans le Conseil hérite du client. Pour sa relance
    # explicite, graph_program_builder passe aussi par le registre.
    features = tuple(
        feature.feature
        for feature in MCP_FEATURES
        if feature.actions or feature.graphs or feature.play_actions
    )
    token = await claude.token(features, "read")
    result, failed = await call(claude, token, "agents_play_list")
    assert not failed, result
    assert {item["graph"] for item in result["data"]} == set(GRAPHS)
