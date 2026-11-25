"""MCP declaration for `auth`: level 4, nothing is exposed (January's sign-in and session)."""

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
