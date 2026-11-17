"""Déclaration MCP de `health` : état des services (lecture seule)."""

from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="health",
    actions=(
        McpAction("GET /health", 1, "health_get_status", "État des services de l'application."),
        McpAction(
            "GET /health/embedding",
            1,
            "health_get_embedding_progress",
            "Progression du téléchargement du modèle d'embeddings.",
        ),
    ),
)
