from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="lab",
    actions=(
        McpAction(
            "GET /lab/overview",
            1,
            "tremplin_overview",
            "Presents Tremplin's sections, the token's tools and the missing prerequisites.",
        ),
        McpAction(
            "GET /lab/preferences",
            1,
            "lab_read_preferences",
            "Reads the pinned activities and the guided tour state.",
        ),
        McpAction(
            "PATCH /lab/preferences",
            2,
            "lab_change_preferences",
            "Changes the list of pinned activities or the guided tour state.",
        ),
    ),
)
