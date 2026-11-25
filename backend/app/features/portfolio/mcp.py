from app.mcp.base import FeatureMcp, McpAction

_PRIVATE = "Private files are reserved for the interface."
_CONFIRM = "Publishing and using the link require an explicit decision in the interface."

MCP = FeatureMcp(
    feature="portfolio",
    actions=(
        McpAction(
            "GET /portfolio",
            1,
            "portfolio_read_private",
            "Reads the account's items and the state of its portfolio.",
            untrusted=("candidates[].label", "candidates[].text", "candidates[].url"),
        ),
        McpAction(
            "POST /portfolio/drafts",
            3,
            "portfolio_prepare_draft",
            "Creates the private draft and its files. Asks for confirmation.",
            side_effects="external",
        ),
        McpAction(
            "GET /portfolio/drafts/{draft_id}/preview",
            1,
            "portfolio_open_draft_preview",
            "Reads the private preview's metadata and gives its local link.",
            artifact=True,
        ),
        McpAction(
            "GET /portfolio/drafts/{draft_id}/zip",
            1,
            "portfolio_get_draft_archive",
            "Reads the private archive's metadata and gives its local link.",
            artifact=True,
        ),
        McpAction(
            "GET /public/portfolios/{slug}",
            1,
            "portfolio_open_public_portfolio",
            "Checks that a published portfolio is available and gives its local link.",
            artifact=True,
        ),
        McpAction(
            "POST /portfolio/publish",
            3,
            "portfolio_publish_site",
            "Publishes the portfolio at its public link. Asks for confirmation.",
            side_effects="external",
        ),
        McpAction(
            "POST /portfolio/withdraw",
            3,
            "portfolio_withdraw_site",
            "Withdraws the published portfolio. Asks for confirmation.",
            side_effects="external",
        ),
        McpAction(
            "PUT /portfolio/links/{target}",
            3,
            "portfolio_set_profile_link",
            "Chooses whether the public link appears in a profile. Asks for confirmation.",
            side_effects="external",
        ),
    ),
)
