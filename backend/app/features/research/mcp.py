"""Déclaration MCP de `research` : usage de la recherche web et sources d'une session."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="research",
    actions=(
        McpAction(
            "GET /research/usage",
            1,
            "research_get_usage",
            "Compteur du mois de la recherche web (Brave).",
        ),
        McpAction(
            "GET /research/sources",
            1,
            "research_list_sources",
            "Les pages lues et jugées par une session de recherche (`session_id`).",
            untrusted=("[].title", "[].author", "[].reason", "[].url"),
        ),
    ),
    graphs=(
        McpGraph(
            "web_research",
            summary="Recherche sur le web : une question (`query`) et des liens facultatifs "
            "(`urls`) ; les pages utiles entrent en mémoire.",
            untrusted=("result",),
        ),
    ),
)
