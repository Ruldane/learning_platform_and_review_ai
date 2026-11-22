"""Ton futur toi en lecture seule au niveau 1."""

from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="future_self",
    actions=(
        McpAction(
            "GET /future-self",
            1,
            "future_self_get_projection",
            "Compare les rythmes d'étude pour un poste (`role`), une zone (`zone`) et un programme "
            "validé (`program_id`). `alternative_weekly_minutes` simule une autre disponibilité "
            "hebdomadaire. `target_percent` indique la part d'offres visée (60 par défaut).",
            untrusted=("recommendations[].chapter.title", "recommendations[].chapter.skills[]"),
        ),
    ),
)
