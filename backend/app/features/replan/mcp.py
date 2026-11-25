"""MCP declaration for `replan`: replan a program and read its history."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="replan",
    actions=(
        McpAction(
            "POST /programs/{program_id}/replan",
            2,
            "replan_start_replan",
            'Starts a replan ("this week I only have 5 hours"): the Strategist '
            "proposes, nothing is written without January's answer.",
            launches="replan",
        ),
        McpAction(
            "GET /programs/{program_id}/versions",
            1,
            "replan_list_versions",
            "The plan versions of a program, most recent first.",
        ),
    ),
    graphs=(
        McpGraph(
            "replan",
            follow_only=True,
            summary="Replans a program (`program_id`, `trigger`, optional message).",
        ),
    ),
)
