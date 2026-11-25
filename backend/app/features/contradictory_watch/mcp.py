from app.mcp.base import FeatureMcp, McpAction

_TEXT = ("title", "sources[].claim", "protocol", "criterion", "observation.measurement")


MCP = FeatureMcp(
    feature="contradictory_watch",
    actions=(
        McpAction(
            "GET /contradictory-watch",
            1,
            "contradictory_watch_list",
            "Lists the private watch experiments.",
            untrusted=tuple(f"[].{path}" for path in _TEXT),
        ),
        McpAction(
            "GET /contradictory-watch/{experiment_id}",
            1,
            "contradictory_watch_read",
            "Reads an experiment's frozen sources and measurements.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /contradictory-watch",
            2,
            "contradictory_watch_create",
            "Freezes two references and an experiment protocol.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /contradictory-watch/{experiment_id}/observations",
            2,
            "contradictory_watch_observe",
            "Records the measurement taken and the agreed result.",
            untrusted=_TEXT,
        ),
    ),
)
