"""Le consentement et les événements privés sont accessibles depuis l’interface."""

from app.mcp.base import FeatureMcp

MCP = FeatureMcp(
    feature="calendar",
    excluded={
        route: "Accès Agenda personnel, réservé au consentement explicite dans l’interface."
        for route in (
            "GET /calendar/connection",
            "POST /calendar/connection",
            "GET /calendar/callback",
            "DELETE /calendar/connection",
            "POST /calendar/proposals",
            "POST /calendar/proposals/{proposal_id}/confirm",
            "GET /calendar/upcoming",
        )
    },
)
