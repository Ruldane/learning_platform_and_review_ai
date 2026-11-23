from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="lab",
    actions=(
        McpAction(
            "GET /lab/overview",
            1,
            "tremplin_overview",
            "Présente les rubriques de Tremplin, les outils du jeton et les prérequis manquants.",
        ),
        McpAction(
            "GET /lab/preferences",
            1,
            "lab_read_preferences",
            "Lit les activités épinglées et l'état de la visite guidée.",
        ),
        McpAction(
            "PATCH /lab/preferences",
            2,
            "lab_change_preferences",
            "Change la liste des activités épinglées ou l'état de la visite guidée.",
        ),
    ),
)
