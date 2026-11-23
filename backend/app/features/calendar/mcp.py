"""Le MCP relit le prochain créneau et prépare une proposition sur consentement."""

from app.mcp.base import FeatureMcp, McpAction, McpExclusion

MCP = FeatureMcp(
    feature="calendar",
    actions=(
        McpAction(
            "GET /calendar/upcoming",
            1,
            "calendar_read_upcoming",
            "Relit la date du prochain créneau déjà confirmé dans Tremplin.",
        ),
        McpAction(
            "POST /calendar/proposals",
            3,
            "calendar_prepare_proposal",
            "Il faut confirmer la consultation de Google Agenda pour préparer une proposition.",
            untrusted=("title",),
            side_effects="external",
        ),
        McpAction(
            "GET /calendar/connection",
            1,
            "calendar_read_connection",
            "Lit l’état du consentement Agenda du compte.",
        ),
        McpAction(
            "DELETE /calendar/connection",
            3,
            "calendar_disconnect_agenda",
            "Retire l’accès à Google Agenda. Demande à confirmer.",
            side_effects="external",
        ),
        McpAction(
            "POST /calendar/proposals/{proposal_id}/confirm",
            3,
            "calendar_confirm_proposal",
            "Inscrit le créneau proposé dans Google Agenda après consentement. "
            "Demande à confirmer.",
            side_effects="external",
            untrusted=("title",),
        ),
    ),
    excluded={
        "POST /calendar/connection": McpExclusion.CALENDAR_OAUTH,
        "GET /calendar/callback": McpExclusion.CALENDAR_OAUTH,
    },
)
