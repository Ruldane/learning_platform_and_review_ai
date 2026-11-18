"""Déclaration MCP de la carte de compétences et de la création au référentiel."""

from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="skills",
    actions=(
        McpAction(
            "POST /skills",
            2,
            "skills_write_skill",
            "Ajoute une compétence au référentiel, sans attribuer de niveau ni de preuve.",
        ),
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
