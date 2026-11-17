"""Déclaration MCP de `postings` : ajouter une offre (lien ou texte), la lire, la retirer.

Le texte d'une offre vient du web : tout ce que la réponse en cite est rendu comme donnée, jamais
comme consigne."""

from app.mcp.base import FeatureMcp, McpAction

_TEXT = ("title", "company", "text", "url", "analysis", "duplicates")

MCP = FeatureMcp(
    feature="postings",
    actions=(
        McpAction(
            "POST /postings",
            2,
            "postings_add_posting",
            "Ajoute une offre par son lien (`url`) ou son texte collé (`text`) et lance "
            "l'analyse ; la même offre rend l'existante.",
            untrusted=tuple(f"posting.{name}" for name in _TEXT),
            launches="gap_analysis",
        ),
        McpAction(
            "GET /postings",
            1,
            "postings_list_postings",
            "Les offres de January, les plus récentes d'abord.",
            untrusted=("[].title", "[].company"),
        ),
        McpAction(
            "GET /postings/{posting_id}",
            1,
            "postings_get_posting",
            "Une offre : texte figé, analyse, doublons.",
            untrusted=_TEXT,
        ),
        McpAction(
            "DELETE /postings/{posting_id}",
            3,
            "postings_delete_posting",
            "Retire l'offre, son élément de mémoire, ses revues et ses versions de CV (PDF et "
            "images compris) : demande à confirmer.",
            side_effects="external",
        ),
        McpAction(
            "POST /postings/{posting_id}/distinct",
            2,
            "postings_mark_distinct",
            "Marque deux offres comme distinctes : le doublon disparaît des deux côtés.",
        ),
        McpAction(
            "POST /postings/{posting_id}/gap",
            2,
            "postings_relaunch_gap",
            "Relance l'analyse d'écart d'une offre.",
        ),
    ),
)
