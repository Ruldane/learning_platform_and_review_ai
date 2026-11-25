"""Le MCP relit le prochain créneau et prépare une proposition sur consentement."""

from app.mcp.base import FeatureMcp, McpAction, McpExclusion

MCP = FeatureMcp(
    feature="calendar",
    actions=(
        McpAction(
            "GET /calendar/upcoming",
            1,
            "calendar_read_upcoming",
            "Reads the date of the next slot already confirmed in Tremplin.",
        ),
        McpAction(
            "POST /calendar/proposals",
            3,
            "calendar_prepare_proposal",
            "Prepares a slot proposal; reading Google Calendar requires confirmation.",
            untrusted=("title",),
            side_effects="external",
        ),
        McpAction(
            "GET /calendar/connection",
            1,
            "calendar_read_connection",
            "Reads the account's Calendar consent status.",
        ),
        McpAction(
            "DELETE /calendar/connection",
            3,
            "calendar_disconnect_agenda",
            "Revokes access to Google Calendar. Requires confirmation.",
            side_effects="external",
        ),
        McpAction(
            "POST /calendar/proposals/{proposal_id}/confirm",
            3,
            "calendar_confirm_proposal",
            "Adds the proposed slot to Google Calendar after consent. Requires confirmation.",
            side_effects="external",
            untrusted=("title",),
        ),
    ),
    excluded={
        "POST /calendar/connection": McpExclusion.CALENDAR_OAUTH,
        "GET /calendar/callback": McpExclusion.CALENDAR_OAUTH,
    },
)
