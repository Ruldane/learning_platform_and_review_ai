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
            "Starts a quick capture of a single source: a text, a link or an already imported "
            "document; the Archivist files the result in memory.",
            launches="capture",
        ),
        McpAction(
            "GET /journal",
            1,
            "capture_read_journal",
            "The journal: captures, sessions, quizzes and reviews, newest first.",
        ),
    ),
    graphs=(
        McpGraph(
            "capture",
            follow_only=True,
            summary="Quick capture: a single source among `url`, `text` or `document_id`.",
        ),
    ),
)
