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
            "Starts a market scan (`role`, `zone` optional, remembered in the settings).",
            launches="market_radar",
        ),
        McpAction(
            "GET /radar/latest",
            1,
            "radar_get_latest",
            "The latest finished scan, the scan in progress and the default suggested role.",
            untrusted=tuple(f"latest.{path}" for path in _OFFERS),
        ),
        McpAction("GET /radar/runs", 1, "radar_list_runs", "The 20 latest market scans."),
        McpAction(
            "GET /radar/runs/{run_id}",
            1,
            "radar_get_run",
            "A scan: skill ranking, alerts, postings read.",
            untrusted=_OFFERS,
        ),
    ),
    graphs=(
        McpGraph(
            "market_radar",
            follow_only=True,
            summary="Market scan (`run_id` of an already created scan).",
            untrusted=("result",),
        ),
    ),
)
