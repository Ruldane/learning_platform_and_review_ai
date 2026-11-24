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
            "Lists the projects already graded.",
            untrusted=("[].title",),
        ),
        McpAction(
            "GET /grade-appeals/projects/{project_id}/criteria",
            1,
            "grade_appeals_criteria",
            "Reads the criteria of the written submission.",
            untrusted=("[].criterion", "[].original_comment"),
        ),
        McpAction(
            "GET /grade-appeals",
            1,
            "grade_appeals_list",
            "Lists the account's grade appeals.",
            untrusted=tuple(f"[].{path}" for path in _TEXT),
        ),
        McpAction(
            "GET /grade-appeals/{appeal_id}",
            1,
            "grade_appeals_read",
            "Reads both justifications and the recorded decision.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /grade-appeals",
            2,
            "grade_appeals_create",
            "Freezes the submission, the criterion and the reason of an appeal.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /grade-appeals/{appeal_id}/review",
            3,
            "grade_appeals_review",
            "Asks for confirmation before sending the submission to the second reader.",
            side_effects="external",
            launches=APPEAL_GRAPH,
        ),
        McpAction(
            "POST /grade-appeals/{appeal_id}/decision",
            3,
            "grade_appeals_decide_appeal",
            "Records the appeal decision. Asks for confirmation.",
        ),
    ),
    graphs=(McpGraph(APPEAL_GRAPH, follow_only=True),),
)
