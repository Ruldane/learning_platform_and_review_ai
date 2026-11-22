from app.mcp.base import FeatureMcp, McpAction

_ROOT = "/contributions"
_ONE = _ROOT + "/{contribution_id}"
_DOSSIER_FIELDS = (
    "issue.title",
    "issue.body",
    "issue.url",
    "publication_url",
    "pull_url",
    "cv_line",
)

MCP = FeatureMcp(
    feature="contributions",
    actions=(
        McpAction(
            f"GET {_ROOT}/suggestions",
            1,
            "contributions_list_suggestions",
            "Issues publiques pour le chapitre en cours du programme.",
            untrusted=("items[].title", "items[].body", "items[].url"),
        ),
        McpAction(
            f"GET {_ROOT}",
            1,
            "contributions_list_dossiers",
            "Dossiers de contribution de l’utilisatrice.",
            untrusted=tuple(f"[].{field}" for field in _DOSSIER_FIELDS),
        ),
        McpAction(
            f"GET {_ONE}",
            1,
            "contributions_read_dossier",
            "Lit le dossier et sa pull request éventuelle.",
            untrusted=_DOSSIER_FIELDS,
        ),
        McpAction(
            f"POST {_ROOT}",
            3,
            "contributions_create_dossier",
            "Crée un dossier depuis une issue du programme. À confirmer.",
            untrusted=_DOSSIER_FIELDS,
        ),
        McpAction(
            f"POST {_ONE}/publication",
            3,
            "contributions_prepare_publication",
            "Prépare le lien de publication GitHub avec le texte et les branches. À confirmer.",
            side_effects="external",
            untrusted=_DOSSIER_FIELDS,
        ),
        McpAction(
            f"POST {_ONE}/pull",
            3,
            "contributions_track_pull",
            "Vérifie et lie la pull request à son dossier. À confirmer.",
            untrusted=_DOSSIER_FIELDS,
        ),
        McpAction(
            f"POST {_ONE}/refresh",
            3,
            "contributions_refresh_pull",
            "Relit la pull request et inscrit la preuve après fusion. À confirmer.",
            untrusted=_DOSSIER_FIELDS,
        ),
    ),
)
