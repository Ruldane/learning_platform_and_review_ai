from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="ghost",
    actions=(
        McpAction(
            "GET /quizzes/{quiz_id}/ghost",
            1,
            "ghost_read_quiz",
            "Reads the markers of your own past attempts at a quiz, without their answers.",
        ),
        McpAction(
            "GET /ide/sessions/{session_id}/ghost",
            1,
            "ghost_read_ide",
            "Reads the markers of your own past checks on an IDE exercise, without output.",
        ),
    ),
)
