"""Déclaration MCP de `capture` : la capture rapide (lien, texte ou document déjà importé) et le
journal."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="capture",
    actions=(
        McpAction(
            "POST /capture",
            2,
            "capture_start_capture",
            "Lance la capture rapide d'une seule source : un texte, un lien ou un document déjà "
            "importé ; l'Archiviste range le résultat en mémoire.",
            launches="capture",
        ),
        McpAction(
            "GET /journal",
            1,
            "capture_read_journal",
            "Le journal : captures, sessions, quiz et bilans, du plus récent au plus ancien.",
        ),
    ),
    graphs=(
        McpGraph(
            "capture",
            follow_only=True,
            summary="Capture rapide : une seule source parmi `url`, `text` ou `document_id`.",
        ),
    ),
)
