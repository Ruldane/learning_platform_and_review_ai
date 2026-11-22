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
            "Liste les programmes validés accessibles pour une semaine commune.",
            untrusted=("[].title",),
        ),
        McpAction(
            "GET /interprogram-planning",
            1,
            "interprogram_planning_list_proposals",
            "Relit les propositions de planning entre programmes du compte.",
            untrusted=tuple(f"[].{item}" for item in _TEXT),
        ),
        McpAction(
            "POST /interprogram-planning",
            2,
            "interprogram_planning_prepare_week",
            "Prépare une semaine commune à partir des programmes choisis et des créneaux locaux.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /interprogram-planning/{proposal_id}/accept",
            2,
            "interprogram_planning_accept_week",
            "Applique la semaine après confirmation explicite et relecture des contraintes.",
            untrusted=_TEXT,
        ),
    ),
)
