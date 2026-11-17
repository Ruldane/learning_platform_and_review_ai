"""Déclaration MCP de `radar` : le radar du marché. Les offres lues viennent du web : leurs titres
et entreprises sont rendus comme données."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

_OFFERS = ("offers[].url", "offers[].title", "offers[].company")

MCP = FeatureMcp(
    feature="radar",
    actions=(
        McpAction(
            "POST /radar/runs",
            2,
            "radar_start_run",
            "Lance un relevé du marché (`role`, `zone` facultatifs, mémorisés dans les réglages).",
            launches="market_radar",
        ),
        McpAction(
            "GET /radar/latest",
            1,
            "radar_get_latest",
            "Le dernier relevé fini, le relevé en cours et le poste proposé par défaut.",
            untrusted=tuple(f"latest.{path}" for path in _OFFERS),
        ),
        McpAction("GET /radar/runs", 1, "radar_list_runs", "Les 20 derniers relevés du marché."),
        McpAction(
            "GET /radar/runs/{run_id}",
            1,
            "radar_get_run",
            "Un relevé : classement des compétences, alertes, offres lues.",
            untrusted=_OFFERS,
        ),
    ),
    graphs=(
        McpGraph(
            "market_radar",
            follow_only=True,
            summary="Relevé du marché (`run_id` d'un relevé déjà créé).",
            untrusted=("result",),
        ),
    ),
)
