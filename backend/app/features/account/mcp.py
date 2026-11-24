"""Demande de suppression du compte et lien local vers son archive."""

from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="account",
    actions=(
        McpAction(
            "GET /account/export",
            1,
            "account_export_data",
            "Gives the local link to download the archive of her data.",
            artifact=True,
        ),
        McpAction(
            "POST /account/delete",
            3,
            "account_delete_data",
            "Erases all account data. Needs confirmation in Tremplin.",
            side_effects="external",
        ),
    ),
)
