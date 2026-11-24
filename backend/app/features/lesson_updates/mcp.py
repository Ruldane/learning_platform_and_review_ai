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
            "Reads a lesson's documented version corrections.",
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
            "Applies the proposed correction to the lesson. Asks for confirmation.",
        ),
    ),
    graphs=(McpGraph(GRAPH, follow_only=True),),
)
