from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="galaxy",
    actions=(
        McpAction(
            "GET /galaxy",
            1,
            "galaxy_read_graph",
            "Lit les compétences, les écarts et les notes actives de la Galaxie.",
            untrusted=("target_label", "nodes[].title", "nodes[].domain", "nodes[].action.ref"),
        ),
    ),
)
