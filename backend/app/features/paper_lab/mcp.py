"""Actions privées du parcours Du papier au code."""

from app.agents.tools.paper_lab_port import PAPER_GRAPH
from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="paper_lab",
    actions=(
        McpAction(
            "GET /paper-labs",
            1,
            "paper_lab_list",
            "Lists the account's mini-courses.",
            untrusted=("[].url", "[].title"),
        ),
        McpAction(
            "GET /paper-labs/{lab_id}",
            1,
            "paper_lab_get",
            "Reads the mini-course and the expected result.",
            untrusted=("url", "title", "source_title", "course", "expected"),
        ),
        McpAction(
            "POST /paper-labs",
            3,
            "paper_lab_prepare",
            "Requests reading a public paper and building its experiment; requires confirmation.",
            side_effects="external",
            launches=PAPER_GRAPH,
        ),
    ),
    graphs=(
        McpGraph(PAPER_GRAPH, follow_only=True, summary="Prepares a mini-course and its notebook."),
    ),
)
