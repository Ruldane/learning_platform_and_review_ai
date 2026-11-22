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
            "Propose d'ajouter des lignes « À ajouter » ou « Hors périmètre » cochées (`skills`) "
            "au programme validé choisi (`program_id`, le plus récent par défaut). "
            "January valide la proposition avant toute écriture au calendrier.",
        ),
        McpAction(
            "POST /postings/{posting_id}/gap/validate",
            2,
            "gap_validate_skills",
            "« Je les maîtrise déjà » : ajoute un module « Valider mes acquis » (`skills`) "
            "et lance "
            "son quiz ; January le passe pour faire valider ces compétences.",
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
