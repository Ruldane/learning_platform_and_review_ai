from app.agents.tools.oncall_port import REVIEW_GRAPH
from app.mcp.base import FeatureMcp, McpAction, McpGraph

_GESTURE = "On-call drill: the user's action happens in the interface."

MCP = FeatureMcp(
    feature="oncall",
    actions=(
        McpAction("GET /oncall/incidents", 1, "oncall_list_incidents", "Lists the on-call drills."),
        McpAction(
            "GET /oncall/incidents/{incident_id}",
            1,
            "oncall_get_incident",
            "Reads the state, events and result of a drill.",
            untrusted=("report", "verdict.feedback"),
        ),
        McpAction(
            "POST /oncall/incidents",
            3,
            "oncall_start_incident",
            "Starts an on-call drill. Asks for confirmation.",
        ),
        McpAction(
            "POST /oncall/incidents/{incident_id}/advance",
            3,
            "oncall_advance_incident",
            "Advances the on-call drill. Asks for confirmation.",
        ),
        McpAction(
            "POST /oncall/incidents/{incident_id}/events/{event_id}/observe",
            3,
            "oncall_observe_incident_event",
            "Records an observation in the drill. Asks for confirmation.",
        ),
        McpAction(
            "POST /oncall/incidents/{incident_id}/diagnostic",
            3,
            "oncall_run_incident_diagnostic",
            "Runs the drill's diagnostic. Asks for confirmation.",
            side_effects="external",
        ),
        McpAction(
            "POST /oncall/incidents/{incident_id}/report",
            3,
            "oncall_submit_incident_report",
            "Submits the drill report. Asks for confirmation.",
            launches="oncall_review",
        ),
    ),
    graphs=(McpGraph(REVIEW_GRAPH, follow_only=True),),
)
