from app.agents.tools.grade_appeals_port import APPEAL_GRAPH
from app.mcp.base import FeatureMcp, McpAction, McpGraph

_TEXT = (
    "source.project.title",
    "source.submission",
    "source.criterion.criterion",
    "source.criterion.original_comment",
    "reason",
    "second.comment",
)

MCP = FeatureMcp(
    feature="grade_appeals",
    actions=(
        McpAction(
            "GET /grade-appeals/projects",
            1,
            "grade_appeals_projects",
            "Liste les projets déjà évalués.",
            untrusted=("[].title",),
        ),
        McpAction(
            "GET /grade-appeals/projects/{project_id}/criteria",
            1,
            "grade_appeals_criteria",
            "Relit les critères de la remise écrite.",
            untrusted=("[].criterion", "[].original_comment"),
        ),
        McpAction(
            "GET /grade-appeals",
            1,
            "grade_appeals_list",
            "Liste les contestations de note du compte.",
            untrusted=tuple(f"[].{path}" for path in _TEXT),
        ),
        McpAction(
            "GET /grade-appeals/{appeal_id}",
            1,
            "grade_appeals_read",
            "Relit les deux justifications et la décision enregistrée.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /grade-appeals",
            2,
            "grade_appeals_create",
            "Fige la remise, le critère et le motif d’une contestation.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /grade-appeals/{appeal_id}/review",
            3,
            "grade_appeals_review",
            "Demande de confirmer l’envoi de la remise au second lecteur.",
            side_effects="external",
            launches=APPEAL_GRAPH,
        ),
        McpAction(
            "POST /grade-appeals/{appeal_id}/decision",
            3,
            "grade_appeals_decide_appeal",
            "Enregistre la décision de recours. Demande à confirmer.",
        ),
    ),
    graphs=(McpGraph(APPEAL_GRAPH, follow_only=True),),
)
