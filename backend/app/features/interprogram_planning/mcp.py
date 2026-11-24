from app.mcp.base import FeatureMcp, McpAction

_TEXT = (
    "programs[].title",
    "placements[].title",
    "placements[].module_title",
    "unplaced[].title",
    "unplaced[].module_title",
    "prerequisites[].module.title",
    "prerequisites[].label",
    "prerequisites[].references[].title",
)

MCP = FeatureMcp(
    feature="interprogram_planning",
    actions=(
        McpAction(
            "GET /interprogram-planning/options",
            1,
            "interprogram_planning_list_programs",
            "Lists the validated programs available for a shared week.",
            untrusted=("[].title",),
        ),
        McpAction(
            "GET /interprogram-planning",
            1,
            "interprogram_planning_list_proposals",
            "Reads the account's cross-program planning proposals.",
            untrusted=tuple(f"[].{item}" for item in _TEXT),
        ),
        McpAction(
            "POST /interprogram-planning",
            2,
            "interprogram_planning_prepare_week",
            "Prepares a shared week from the chosen programs and the local time slots.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /interprogram-planning/{proposal_id}/accept",
            2,
            "interprogram_planning_accept_week",
            "Applies the week after explicit confirmation and a review of the constraints.",
            untrusted=_TEXT,
        ),
    ),
)
