"""Déclaration MCP de `health` : état des services (lecture seule)."""

from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="health",
    actions=(
        McpAction("GET /health", 1, "health_get_status", "Status of the application's services."),
        McpAction(
            "GET /health/embedding",
            1,
            "health_get_embedding_progress",
            "Download progress of the embedding model.",
        ),
    ),
)
