from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="skill_market",
    actions=(
        McpAction(
            "GET /skill-market",
            1,
            "skill_market_read",
            "Compare les deux relevés du poste et simule une heure sur la compétence choisie.",
            untrusted=("role", "zone", "quotes[].name", "simulation.skill", "simulation.chapter"),
        ),
    ),
)
