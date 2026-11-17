"""Déclaration MCP de `gap` : l'écart entre le profil de January et une offre."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="gap",
    actions=(
        McpAction(
            "GET /postings/{posting_id}/gap",
            1,
            "gap_get_gap",
            "Le tableau d'écart d'une offre (recalculé à chaque lecture).",
        ),
        McpAction(
            "POST /postings/{posting_id}/gap/plan",
            2,
            "gap_plan_missing_skills",
            "« Ajouter au planning » : lance une replanification qui ajoute les compétences "
            "manquantes (`skills`) ; January la valide avant toute écriture.",
        ),
        McpAction(
            "GET /gap/top-missing",
            1,
            "gap_list_top_missing",
            "Les 10 compétences absentes demandées par le plus d'offres.",
        ),
    ),
    graphs=(
        McpGraph(
            "gap_analysis",
            follow_only=True,
            summary="Analyse l'écart entre une offre (`posting_id`) et le profil de January.",
        ),
    ),
)
