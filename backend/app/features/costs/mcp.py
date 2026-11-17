"""Déclaration MCP de `costs` : coûts de l'IA et journal des appels (lecture seule)."""

from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="costs",
    actions=(
        McpAction(
            "GET /costs",
            1,
            "costs_get_report",
            "Coûts de l'IA sur 7, 30 ou 90 jours, par jour, fonction, agent et modèle.",
        ),
        McpAction(
            "GET /costs/calls",
            1,
            "costs_list_calls",
            "Journal des appels des agents (jamais le contenu des prompts).",
        ),
    ),
)
