"""Déclaration MCP de `costs` : coûts de l'IA et journal des appels (lecture seule)."""

from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="costs",
    actions=(
        McpAction(
            "GET /costs",
            1,
            "costs_get_report",
            "AI costs over 7, 30 or 90 days, by day, feature, agent and model.",
        ),
        McpAction(
            "GET /costs/calls",
            1,
            "costs_list_calls",
            "Log of agent calls (never the prompt content).",
        ),
    ),
)
