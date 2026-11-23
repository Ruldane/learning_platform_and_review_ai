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
            "Relit l’exercice du compte, puis le bilan après ses deux réponses.",
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
            "Lance un défi de lecture depuis une leçon. Demande à confirmer.",
            launches="lesson_hunt",
        ),
        McpAction(
            "POST /lesson-hunts/{hunt_id}/answers",
            3,
            "lesson_hunt_submit_hunt_answers",
            "Remet les réponses du défi de lecture. Demande à confirmer.",
            launches="lesson_hunt",
        ),
    ),
    graphs=(McpGraph("lesson_hunt", follow_only=True),),
)
