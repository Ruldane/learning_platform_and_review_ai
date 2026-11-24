from app.mcp.base import FeatureMcp, McpAction

_OFFER = "/compatible-offers/{run_id}/{ref}"

MCP = FeatureMcp(
    feature="compatible_offers",
    actions=(
        McpAction(
            f"GET {_OFFER}",
            1,
            "compatible_offers_read_gap",
            "Reads the current skill gap for a radar posting.",
            untrusted=("title", "company", "url", "rows[].skill"),
        ),
        McpAction(
            f"POST {_OFFER}/plan",
            2,
            "compatible_offers_plan_gap",
            "Submits the chosen gaps to the Strategist. The schedule changes after validation.",
            launches="replan",
        ),
    ),
)
