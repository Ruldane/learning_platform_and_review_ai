"""Consultation de la copie et de son bilan."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

_HUNT = "/lesson-hunts/{hunt_id}"

MCP = FeatureMcp(
    feature="lesson_hunt",
    actions=(
        McpAction(
            f"GET {_HUNT}",
            1,
            "lesson_hunt_read",
            "Reads the account's exercise, then the assessment after its two answers.",
            untrusted=(
                "title",
                "exercise",
                "responses[]",
                "corrections[].source",
                "corrections[].replacement",
                "corrections[].explanation",
                "assessment.answers[].feedback",
            ),
        ),
        McpAction(
            "POST /lesson-hunts",
            3,
            "lesson_hunt_start_lesson_hunt",
            "Starts a reading challenge from a lesson. Requires confirmation.",
            launches="lesson_hunt",
        ),
        McpAction(
            "POST /lesson-hunts/{hunt_id}/answers",
            3,
            "lesson_hunt_submit_hunt_answers",
            "Submits the reading challenge answers. Requires confirmation.",
            launches="lesson_hunt",
        ),
    ),
    graphs=(McpGraph("lesson_hunt", follow_only=True),),
)
