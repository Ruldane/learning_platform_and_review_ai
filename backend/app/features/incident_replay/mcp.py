from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="incident_replay",
    actions=(
        McpAction(
            "GET /incident-replays/scenarios",
            1,
            "incident_replay_scenarios",
            "Liste les incidents fictifs d’entraînement.",
        ),
        McpAction(
            "GET /incident-replays",
            1,
            "incident_replay_list",
            "Liste les replays privés du compte.",
            untrusted=("[].notes[].hypothesis",),
        ),
        McpAction(
            "GET /incident-replays/{replay_id}",
            1,
            "incident_replay_read",
            "Relit la chronologie et les hypothèses privées.",
            untrusted=("notes[].hypothesis",),
        ),
        McpAction(
            "POST /incident-replays",
            2,
            "incident_replay_create",
            "Démarre un replay à partir d’un incident fictif.",
            untrusted=("notes[].hypothesis",),
        ),
        McpAction(
            "POST /incident-replays/{replay_id}/notes",
            2,
            "incident_replay_annotate",
            "Ajoute une hypothèse à un instant du replay.",
            untrusted=("notes[].hypothesis",),
        ),
    ),
)
