"""Déclaration MCP de `auth` : niveau 4, rien n'est exposé (connexion et session de January)."""

from app.mcp.base import FeatureMcp

_WHY = (
    "Connexion et session de January : niveau 4, jamais exposé au MCP (le jeton MCP n'ouvre "
    "ni ne ferme une session, et ne dit pas qui est connecté)."
)

MCP = FeatureMcp(
    feature="auth",
    excluded={
        route: _WHY
        for route in (
            "GET /auth/me",
            "GET /auth/google/login",
            "GET /auth/google/callback",
            "POST /auth/google/claim",
            "POST /auth/logout",
        )
    },
)
