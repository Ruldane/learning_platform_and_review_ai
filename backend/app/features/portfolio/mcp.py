from app.mcp.base import FeatureMcp, McpAction

_PRIVATE = "Les fichiers privés sont réservés à l’interface."
_CONFIRM = "La publication et l’usage du lien exigent une décision explicite dans l’interface."

MCP = FeatureMcp(
    feature="portfolio",
    actions=(
        McpAction(
            "GET /portfolio",
            1,
            "portfolio_read_private",
            "Relit les éléments du compte et l’état de son portfolio.",
            untrusted=("candidates[].label", "candidates[].text", "candidates[].url"),
        ),
        McpAction(
            "POST /portfolio/drafts",
            3,
            "portfolio_prepare_draft",
            "Il faut confirmer la création du brouillon privé et de ses fichiers.",
            side_effects="external",
        ),
    ),
    excluded={
        "GET /portfolio/drafts/{draft_id}/preview": _PRIVATE,
        "GET /portfolio/drafts/{draft_id}/zip": _PRIVATE,
        "POST /portfolio/publish": _CONFIRM,
        "POST /portfolio/withdraw": _CONFIRM,
        "PUT /portfolio/links/{target}": _CONFIRM,
        "GET /public/portfolios/{slug}": "Cette page publique ne nécessite aucun outil MCP.",
    },
)
