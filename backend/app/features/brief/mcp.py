"""Déclaration MCP de `brief` : le brief du matin."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="brief",
    actions=(
        McpAction(
            "GET /brief/today",
            1,
            "brief_get_today",
            "Le brief du jour (bloc, révisions, relances, offres, ressource, conseil).",
            untrusted=("resource", "offers"),
        ),
    ),
    graphs=(
        McpGraph(
            "daily_brief",
            follow_only=True,
            summary="Écrit le conseil et la ressource du brief du jour (`brief_id`).",
        ),
    ),
    play_actions=(McpAction("GET /brief/today", 2, "brief_play_today", launches="daily_brief"),),
)
