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
    ),
    excluded={
        f"POST {_ROOT}/{{update_id}}/accept": "L’utilisatrice confirme la retouche dans la leçon."
    },
    graphs=(McpGraph(GRAPH, follow_only=True),),
)
