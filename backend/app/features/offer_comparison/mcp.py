from app.mcp.base import FeatureMcp, McpAction

_NAMES = tuple(
    f"{position}.{field}" for position in ("first", "second") for field in ("title", "company")
)
_FACTS = (
    _NAMES
    + tuple(
        f"{position}.{field}"
        for position in ("first", "second")
        for field in ("location", "remote")
    )
    + ("preferences.preferred_location",)
)
_SAVED = tuple(f"result.{path}" for path in _FACTS)

MCP = FeatureMcp(
    feature="offer_comparison",
    actions=(
        McpAction(
            "GET /offer-comparisons/postings",
            1,
            "offer_comparison_postings",
            "Liste les offres privées prêtes à être comparées.",
            untrusted=("[].title", "[].company"),
        ),
        McpAction(
            "GET /offer-comparisons/preferences",
            1,
            "offer_comparison_preferences",
            "Relit les poids et critères de comparaison du compte.",
            untrusted=("preferred_location",),
        ),
        McpAction(
            "POST /offer-comparisons/preview",
            2,
            "offer_comparison_preview",
            "Calcule scores, revendications manquantes et sensibilité sans sauvegarde.",
            untrusted=_FACTS,
        ),
        McpAction(
            "POST /offer-comparisons",
            2,
            "offer_comparison_save",
            "Enregistre un scénario avec les valeurs et les poids figés.",
            untrusted=_SAVED,
        ),
        McpAction(
            "GET /offer-comparisons",
            1,
            "offer_comparison_list",
            "Liste les comparaisons privées sauvegardées.",
            untrusted=tuple(f"[].{path}" for path in _NAMES),
        ),
        McpAction(
            "GET /offer-comparisons/{scenario_id}",
            1,
            "offer_comparison_read",
            "Relit le résultat figé d’une comparaison d’offres.",
            untrusted=_SAVED,
        ),
    ),
    excluded={
        "PUT /offer-comparisons/preferences": "Choix personnel des critères par défaut du compte.",
    },
)
