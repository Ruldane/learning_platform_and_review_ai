"""Déclaration MCP de `activity` : le fil d'activité (lecture seule)."""

from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="activity",
    actions=(
        McpAction(
            "GET /activity",
            1,
            "activity_list_events",
            "Le fil d'activité : événements des agents et des tâches de fond, du plus récent "
            "au plus ancien.",
        ),
    ),
)
