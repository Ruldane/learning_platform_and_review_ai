"""Le MCP relit le prochain créneau et prépare une proposition sur consentement."""

from app.mcp.base import FeatureMcp, McpAction

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
    ),
    excluded={
        route: "Accès Agenda personnel, réservé au consentement explicite dans l’interface."
        for route in (
            "GET /calendar/connection",
            "POST /calendar/connection",
            "GET /calendar/callback",
            "DELETE /calendar/connection",
            "POST /calendar/proposals/{proposal_id}/confirm",
        )
    },
)
