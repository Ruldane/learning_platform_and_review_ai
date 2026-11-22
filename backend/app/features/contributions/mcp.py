from app.mcp.base import FeatureMcp, McpAction

_ROOT = "/contributions"
_ONE = _ROOT + "/{contribution_id}"

MCP = FeatureMcp(
    feature="contributions",
    actions=(
        McpAction(
            f"GET {_ROOT}/suggestions",
            1,
            "contributions_list_suggestions",
            "Issues publiques pour le chapitre en cours du programme.",
        ),
        McpAction(
            f"GET {_ROOT}",
            1,
            "contributions_list_dossiers",
            "Dossiers de contribution de l’utilisatrice.",
        ),
        McpAction(
            f"GET {_ONE}",
            1,
            "contributions_read_dossier",
            "Lit le dossier et sa pull request éventuelle.",
        ),
        McpAction(
            f"POST {_ROOT}",
            2,
            "contributions_create_dossier",
            "Crée un dossier depuis une issue du programme.",
        ),
        McpAction(
            f"POST {_ONE}/publication",
            3,
            "contributions_prepare_publication",
            "Prépare le lien de publication GitHub avec le texte et les branches. À confirmer.",
            side_effects="external",
            untrusted=("title", "body"),
        ),
        McpAction(
            f"POST {_ONE}/pull",
            2,
            "contributions_track_pull",
            "Vérifie et lie la pull request à son dossier.",
        ),
        McpAction(
            f"POST {_ONE}/refresh",
            2,
            "contributions_refresh_pull",
            "Relit la pull request et inscrit la preuve si elle a été fusionnée.",
        ),
    ),
)
