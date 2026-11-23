from app.mcp.base import FeatureMcp, McpAction

_PRIVATE = "Les fichiers privés sont réservés à l’interface."
_CONFIRM = "La publication et l’usage du lien exigent une décision explicite dans l’interface."

MCP = FeatureMcp(
    feature="portfolio",
    actions=(
        McpAction(
            "GET /portfolio",
            1,
            "portfolio_read_private",
            "Relit les éléments du compte et l’état de son portfolio.",
            untrusted=("candidates[].label", "candidates[].text", "candidates[].url"),
        ),
        McpAction(
            "POST /portfolio/drafts",
            3,
            "portfolio_prepare_draft",
            "Il faut confirmer la création du brouillon privé et de ses fichiers.",
            side_effects="external",
        ),
        McpAction(
            "GET /portfolio/drafts/{draft_id}/preview",
            1,
            "portfolio_open_draft_preview",
            "Lit les métadonnées de la prévisualisation privée et donne son lien local.",
            artifact=True,
        ),
        McpAction(
            "GET /portfolio/drafts/{draft_id}/zip",
            1,
            "portfolio_get_draft_archive",
            "Lit les métadonnées de l’archive privée et donne son lien local.",
            artifact=True,
        ),
        McpAction(
            "GET /public/portfolios/{slug}",
            1,
            "portfolio_open_public_portfolio",
            "Vérifie la disponibilité d’un portfolio publié et donne son lien local.",
            artifact=True,
        ),
        McpAction(
            "POST /portfolio/publish",
            3,
            "portfolio_publish_site",
            "Publie le portfolio sur son lien public. Demande à confirmer.",
            side_effects="external",
        ),
        McpAction(
            "POST /portfolio/withdraw",
            3,
            "portfolio_withdraw_site",
            "Retire le portfolio publié. Demande à confirmer.",
            side_effects="external",
        ),
        McpAction(
            "PUT /portfolio/links/{target}",
            3,
            "portfolio_set_profile_link",
            "Choisit si le lien public apparaît dans un profil. Demande à confirmer.",
            side_effects="external",
        ),
    ),
)
