"""Déclaration MCP de `auth` : niveau 4, rien n'est exposé (connexion et session de January)."""

from app.mcp.base import FeatureMcp, McpExclusion

MCP = FeatureMcp(
    feature="auth",
    excluded={
        route: McpExclusion.AUTH
        for route in (
            "GET /auth/me",
            "GET /auth/google/login",
            "GET /auth/google/callback",
            "POST /auth/google/claim",
            "POST /auth/logout",
        )
    },
)
