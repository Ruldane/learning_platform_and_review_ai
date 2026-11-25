from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="galaxy",
    actions=(
        McpAction(
            "GET /galaxy",
            1,
            "galaxy_read_graph",
            "Reads the Galaxy's skills, gaps and active notes.",
            untrusted=("target_label", "nodes[].title", "nodes[].domain", "nodes[].action.ref"),
        ),
    ),
)
