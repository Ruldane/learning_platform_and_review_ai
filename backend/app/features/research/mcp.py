"""MCP declaration for `research`: web search usage and the sources of a session."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="research",
    actions=(
        McpAction(
            "GET /research/usage",
            1,
            "research_get_usage",
            "This month's web search counter (Brave).",
        ),
        McpAction(
            "GET /research/sources",
            1,
            "research_list_sources",
            "The pages read and assessed by a research session (`session_id`).",
            untrusted=("[].title", "[].author", "[].reason", "[].url"),
        ),
    ),
    graphs=(
        McpGraph(
            "web_research",
            summary="Web research: a question (`query`) and optional links "
            "(`urls`); useful pages go into memory.",
            untrusted=("result",),
        ),
    ),
)
