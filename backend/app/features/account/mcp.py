"""Demande de suppression du compte et lien local vers son archive."""

from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="account",
    actions=(
        McpAction(
            "GET /account/export",
            1,
            "account_export_data",
            "Donne le lien local pour télécharger l’archive de ses données.",
            artifact=True,
        ),
        McpAction(
            "POST /account/delete",
            3,
            "account_delete_data",
            "Efface toutes les données du compte. Demande à confirmer dans Tremplin.",
            side_effects="external",
        ),
    ),
)
