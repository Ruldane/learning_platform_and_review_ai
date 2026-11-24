"""Déclaration MCP de `activity` : le fil d'activité (lecture seule)."""

from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="activity",
    actions=(
        McpAction(
            "GET /activity",
            1,
            "activity_list_events",
            "The activity feed: agent and background-job events, newest first.",
        ),
    ),
)
