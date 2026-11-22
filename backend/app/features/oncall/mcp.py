from app.agents.tools.oncall_port import REVIEW_GRAPH
from app.mcp.base import FeatureMcp, McpAction, McpGraph

_GESTURE = "Exercice d’astreinte : le geste de l’utilisatrice se fait dans l’interface."

MCP = FeatureMcp(
    feature="oncall",
    actions=(
        McpAction(
            "GET /oncall/incidents", 1, "oncall_list_incidents", "Liste les exercices d’astreinte."
        ),
        McpAction(
            "GET /oncall/incidents/{incident_id}",
            1,
            "oncall_get_incident",
            "Lit l’état, les événements et le résultat d’un exercice.",
            untrusted=("report", "verdict.feedback"),
        ),
    ),
    graphs=(McpGraph(REVIEW_GRAPH, follow_only=True),),
    excluded={
        "POST /oncall/incidents": _GESTURE,
        "POST /oncall/incidents/{incident_id}/advance": _GESTURE,
        "POST /oncall/incidents/{incident_id}/events/{event_id}/observe": _GESTURE,
        "POST /oncall/incidents/{incident_id}/diagnostic": _GESTURE,
        "POST /oncall/incidents/{incident_id}/report": _GESTURE,
    },
)
