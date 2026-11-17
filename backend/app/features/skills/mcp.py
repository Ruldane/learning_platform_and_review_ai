"""Déclaration MCP de `skills` : la carte de compétences (lecture seule)."""

from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="skills",
    actions=(
        McpAction(
            "GET /skills/graph",
            1,
            "skills_get_graph",
            "Compétences, prérequis et radar par domaine.",
        ),
        McpAction(
            "GET /skills/compare",
            1,
            "skills_compare_skills",
            "Compare les compétences de January au poste cible ou à une offre.",
        ),
        McpAction(
            "GET /skills/history",
            1,
            "skills_get_history",
            "Relevés hebdomadaires de la carte de compétences.",
        ),
        McpAction(
            "GET /skills/{skill_id}",
            1,
            "skills_get_skill",
            "Détail d'une compétence : preuves, offres qui la citent, prochaine action.",
        ),
    ),
)
