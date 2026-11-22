from app.mcp.base import FeatureMcp

_PRIVATE = "La sélection et les fichiers privés sont réservés à l’interface."
_CONFIRM = "La publication et l’usage du lien exigent une décision explicite dans l’interface."

MCP = FeatureMcp(
    feature="portfolio",
    excluded={
        "GET /portfolio": _PRIVATE,
        "POST /portfolio/drafts": _PRIVATE,
        "GET /portfolio/drafts/{draft_id}/preview": _PRIVATE,
        "GET /portfolio/drafts/{draft_id}/zip": _PRIVATE,
        "POST /portfolio/publish": _CONFIRM,
        "POST /portfolio/withdraw": _CONFIRM,
        "PUT /portfolio/links/{target}": _CONFIRM,
        "GET /public/portfolios/{slug}": "Cette page publique ne nécessite aucun outil MCP.",
    },
)
