from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="incident_replay",
    actions=(
        McpAction(
            "GET /incident-replays/scenarios",
            1,
            "incident_replay_scenarios",
            "Lists the fictional training incidents.",
        ),
        McpAction(
            "GET /incident-replays",
            1,
            "incident_replay_list",
            "Lists the account's private replays.",
            untrusted=("[].notes[].hypothesis",),
        ),
        McpAction(
            "GET /incident-replays/{replay_id}",
            1,
            "incident_replay_read",
            "Reads the timeline and the private hypotheses.",
            untrusted=("notes[].hypothesis",),
        ),
        McpAction(
            "POST /incident-replays",
            2,
            "incident_replay_create",
            "Starts a replay from a fictional incident.",
            untrusted=("notes[].hypothesis",),
        ),
        McpAction(
            "POST /incident-replays/{replay_id}/notes",
            2,
            "incident_replay_annotate",
            "Adds a hypothesis at a point in the replay.",
            untrusted=("notes[].hypothesis",),
        ),
    ),
)
