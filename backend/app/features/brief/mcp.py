"""MCP declaration for `brief`: the morning brief."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="brief",
    actions=(
        McpAction(
            "GET /brief/today",
            1,
            "brief_get_today",
            "Today's brief (block, reviews, follow-ups, postings, resource, advice).",
            untrusted=("resource", "offers"),
        ),
    ),
    graphs=(
        McpGraph(
            "daily_brief",
            follow_only=True,
            summary="Writes the advice and resource of today's brief (`brief_id`).",
        ),
    ),
    play_actions=(McpAction("GET /brief/today", 2, "brief_play_today", launches="daily_brief"),),
)
