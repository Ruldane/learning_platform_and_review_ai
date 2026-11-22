from app.mcp.base import FeatureMcp, McpAction

_TEXT = ("title", "sources[].claim", "protocol", "criterion", "observation.measurement")


MCP = FeatureMcp(
    feature="contradictory_watch",
    actions=(
        McpAction(
            "GET /contradictory-watch",
            1,
            "contradictory_watch_list",
            "Liste les expériences privées de veille.",
            untrusted=tuple(f"[].{path}" for path in _TEXT),
        ),
        McpAction(
            "GET /contradictory-watch/{experiment_id}",
            1,
            "contradictory_watch_read",
            "Relit les sources et mesures figées d’une expérience.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /contradictory-watch",
            2,
            "contradictory_watch_create",
            "Fige deux références et un protocole d’expérience.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /contradictory-watch/{experiment_id}/observations",
            2,
            "contradictory_watch_observe",
            "Enregistre la mesure réalisée et le résultat convenu.",
            untrusted=_TEXT,
        ),
    ),
)
