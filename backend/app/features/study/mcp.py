"""Déclaration MCP de `study` : la session guidée avec le Tuteur."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="study",
    actions=(
        McpAction(
            "POST /study-sessions",
            2,
            "study_start_session",
            "Ouvre une session guidée sur une leçon (ou le bloc du jour) et lance le Tuteur.",
            launches="study_session",
        ),
        McpAction(
            "GET /study-sessions/summary",
            1,
            "study_get_summary",
            "Série, minutes de la semaine, minuteur, session ouverte et bloc du jour.",
        ),
        McpAction(
            "GET /study-sessions/{study_session_id}",
            1,
            "study_get_session",
            "Une session guidée, avec son écran de fin.",
        ),
        McpAction(
            "PATCH /study-sessions/{study_session_id}",
            2,
            "study_update_session",
            "Termine (`finish`) ou abandonne (`cancel`) une session guidée.",
        ),
    ),
    graphs=(
        McpGraph(
            "study_session",
            follow_only=True,
            summary="Le Tuteur conduit une session guidée (`study_session_id`).",
        ),
    ),
)
