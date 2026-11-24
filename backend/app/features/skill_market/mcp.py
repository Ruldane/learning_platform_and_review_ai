from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="skill_market",
    actions=(
        McpAction(
            "GET /skill-market",
            1,
            "skill_market_read",
            "Compares the role's two market snapshots and simulates one hour on the chosen skill.",
            untrusted=("role", "zone", "quotes[].name", "simulation.skill", "simulation.chapter"),
        ),
    ),
)
