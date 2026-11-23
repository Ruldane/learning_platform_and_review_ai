from app.agents.tools.lesson_updates_port import GRAPH
from app.mcp.base import FeatureMcp, McpAction, McpGraph

_ROOT = "/lessons/{lesson_id}/updates"

MCP = FeatureMcp(
    feature="lesson_updates",
    actions=(
        McpAction(
            f"GET {_ROOT}",
            1,
            "lesson_updates_list_proposals",
            "Lit les corrections de version documentées d’une leçon.",
            untrusted=(
                "[].source_url",
                "[].explanation",
                "[].changes[].before",
                "[].changes[].after",
            ),
        ),
        McpAction(
            "POST /lessons/{lesson_id}/updates/{update_id}/accept",
            3,
            "lesson_updates_accept_lesson_update",
            "Applique la correction proposée à la leçon. Demande à confirmer.",
        ),
    ),
    graphs=(McpGraph(GRAPH, follow_only=True),),
)
