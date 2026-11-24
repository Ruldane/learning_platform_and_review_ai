from app.mcp.base import FeatureMcp, McpAction

_EVIDENCE_TEXT = ("title", "finding", "expected")
_EXERCISE_TEXT = tuple(f"evidence[].{field}" for field in _EVIDENCE_TEXT)
_GROUP_TEXT = (
    "label",
    *(f"observations[].evidence.{field}" for field in _EVIDENCE_TEXT),
    *(f"exercise.{field}" for field in _EXERCISE_TEXT),
)

MCP = FeatureMcp(
    feature="error_atlas",
    actions=(
        McpAction(
            "GET /error-atlas",
            1,
            "error_atlas_list_hypotheses",
            "Reads the prerequisite hypotheses, their observed errors and the chosen exercises.",
            untrusted=tuple(f"[].{field}" for field in _GROUP_TEXT),
        ),
        McpAction(
            "GET /error-atlas/evidence",
            1,
            "error_atlas_list_evidence",
            "Lists recent errors from graded quizzes and unmet criteria from projects.",
            untrusted=tuple(f"[].{field}" for field in _EVIDENCE_TEXT),
        ),
        McpAction(
            "POST /error-atlas/observations",
            2,
            "error_atlas_record_observation",
            "Links a verified error to a chosen hypothesis with the given confidence level.",
            untrusted=_GROUP_TEXT,
        ),
        McpAction(
            "POST /error-atlas/hypotheses/{hypothesis_id}/exercise",
            2,
            "error_atlas_choose_exercise",
            "Freezes a private remedial sheet with the observations cited in the hypothesis.",
            untrusted=_EXERCISE_TEXT,
        ),
    ),
)
