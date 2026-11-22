from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="ghost",
    actions=(
        McpAction(
            "GET /quizzes/{quiz_id}/ghost",
            1,
            "ghost_read_quiz",
            "Lit les repères des tentatives personnelles d’un quiz, sans leurs réponses.",
        ),
        McpAction(
            "GET /ide/sessions/{session_id}/ghost",
            1,
            "ghost_read_ide",
            "Lit les repères des vérifications personnelles d’un exercice IDE, sans leur sortie.",
        ),
    ),
)
