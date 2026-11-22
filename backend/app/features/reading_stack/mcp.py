"""Outils de lecture et actions explicites de la pile."""

from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="reading_stack",
    actions=(
        McpAction(
            "GET /reading-stack",
            1,
            "reading_stack_list",
            "Liste les éléments de la pile.",
            untrusted=("items[].title", "items[].summary", "items[].reason", "items[].company"),
        ),
        McpAction(
            "GET /reading-stack/{item_id}",
            1,
            "reading_stack_read",
            "Affiche la lecture, sa source et son texte accessible.",
            untrusted=(
                "title",
                "summary",
                "text",
                "reason",
                "company",
                "annotations[].term",
                "annotations[].definition",
                "annotations[].chapter",
            ),
        ),
        McpAction(
            "PATCH /reading-stack/{item_id}",
            2,
            "reading_stack_mark",
            "Marque comme lu ou non lu.",
            untrusted=("title", "summary", "text", "reason", "company"),
        ),
        McpAction(
            "GET /reading-stack/sources",
            1,
            "reading_stack_list_sources",
            "Liste les sources configurées pour la pile.",
            untrusted=("[].label", "[].value"),
        ),
        McpAction(
            "POST /reading-stack/sources",
            2,
            "reading_stack_add_source",
            "Enregistre un sujet, un domaine ou un flux RSS.",
            untrusted=("label", "value"),
        ),
        McpAction(
            "PATCH /reading-stack/sources/{source_id}",
            2,
            "reading_stack_pause_source",
            "Suspend ou reprend la collecte d’une source.",
            untrusted=("label", "value"),
        ),
        McpAction(
            "DELETE /reading-stack/sources/{source_id}",
            3,
            "reading_stack_remove_source",
            "Retire une source de la collecte. Demande à confirmer.",
        ),
        McpAction(
            "POST /reading-stack/{item_id}/memory",
            2,
            "reading_stack_keep",
            "Garde l’élément et sa source dans la mémoire.",
        ),
        McpAction(
            "POST /reading-stack/{item_id}/cards",
            2,
            "reading_stack_make_cards",
            "Crée une fiche à réviser à partir du résumé ou d’un passage vérifié du texte.",
        ),
        McpAction(
            "POST /reading-stack/{item_id}/plan",
            2,
            "reading_stack_plan",
            "Propose une lecture dans un programme validé. La modification attend l’accord.",
        ),
        McpAction(
            "POST /reading-stack/{item_id}/application",
            2,
            "reading_stack_create_application",
            "Crée une candidature interne depuis une offre, avec le contrôle de doublons.",
        ),
    ),
)
