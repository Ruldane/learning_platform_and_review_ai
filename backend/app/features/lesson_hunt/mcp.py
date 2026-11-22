"""Consultation de la copie et de son bilan."""

from app.mcp.base import FeatureMcp, McpAction

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
    ),
    excluded={
        "graph:lesson_hunt": "Lancé par POST /lesson-hunts ou par la remise des réponses.",
        "POST /lesson-hunts": "Défi créé à la demande de l’utilisatrice dans la leçon.",
        f"POST {_HUNT}/answers": "Réponses de l’utilisatrice au défi de lecture.",
    },
)
