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
        McpAction(
            "POST /oncall/incidents",
            3,
            "oncall_start_incident",
            "Démarre un exercice d’astreinte. Demande à confirmer.",
        ),
        McpAction(
            "POST /oncall/incidents/{incident_id}/advance",
            3,
            "oncall_advance_incident",
            "Avance l’exercice d’astreinte. Demande à confirmer.",
        ),
        McpAction(
            "POST /oncall/incidents/{incident_id}/events/{event_id}/observe",
            3,
            "oncall_observe_incident_event",
            "Note une observation de l’exercice. Demande à confirmer.",
        ),
        McpAction(
            "POST /oncall/incidents/{incident_id}/diagnostic",
            3,
            "oncall_run_incident_diagnostic",
            "Exécute le diagnostic de l’exercice. Demande à confirmer.",
            side_effects="external",
        ),
        McpAction(
            "POST /oncall/incidents/{incident_id}/report",
            3,
            "oncall_submit_incident_report",
            "Remet le rapport de l’exercice. Demande à confirmer.",
            launches="oncall_review",
        ),
    ),
    graphs=(McpGraph(REVIEW_GRAPH, follow_only=True),),
)
