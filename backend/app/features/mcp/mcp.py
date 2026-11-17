"""Déclaration MCP de `mcp` : niveau 4, rien n'est exposé (le MCP ne se gère pas lui-même)."""

from app.mcp.base import FeatureMcp

_WHY = (
    "Réglages, jetons, confirmations, journal et annulations du MCP : niveau 4, jamais exposé "
    "au MCP (un jeton ne peut ni se créer, ni se confirmer, ni élargir ses droits)."
)

MCP = FeatureMcp(
    feature="mcp",
    excluded={
        route: _WHY
        for route in (
            "GET /mcp/settings",
            "PUT /mcp/settings",
            "GET /mcp/features",
            "GET /mcp/actions",
            "POST /mcp/tokens",
            "GET /mcp/tokens",
            "DELETE /mcp/tokens/{token_id}",
            "GET /mcp/confirmations",
            "POST /mcp/confirmations/{confirmation_id}/confirm",
            "POST /mcp/confirmations/{confirmation_id}/refuse",
            "GET /mcp/calls",
            "GET /mcp/changes",
            "POST /mcp/changes/{call_id}/undo",
        )
    },
)
