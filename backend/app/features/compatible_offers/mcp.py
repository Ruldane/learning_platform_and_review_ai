from app.mcp.base import FeatureMcp, McpAction

_OFFER = "/compatible-offers/{run_id}/{ref}"

MCP = FeatureMcp(
    feature="compatible_offers",
    actions=(
        McpAction(
            f"GET {_OFFER}",
            1,
            "compatible_offers_read_gap",
            "Lit l’écart actuel de compétences d’une offre du radar.",
            untrusted=("title", "company", "url", "rows[].skill"),
        ),
        McpAction(
            f"POST {_OFFER}/plan",
            2,
            "compatible_offers_plan_gap",
            "Soumet les manques choisis au Stratège. Le planning change après validation.",
            launches="replan",
        ),
    ),
)
