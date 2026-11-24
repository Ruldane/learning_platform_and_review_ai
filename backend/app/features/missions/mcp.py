from app.mcp.base import FeatureMcp, McpAction

_TEXT = (
    "posting_title",
    "company",
    "criteria[].text",
    "criteria[].skills[]",
    "criteria[].note",
    "submission.artifact",
)

MCP = FeatureMcp(
    feature="missions",
    actions=(
        McpAction(
            "GET /missions",
            1,
            "missions_list_missions",
            "Lists the 48-hour missions.",
            untrusted=tuple(f"[].{field}" for field in _TEXT),
        ),
        McpAction(
            "GET /missions/{mission_id}",
            1,
            "missions_get_mission",
            "Reads a mission, its measurements and its submission proof.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /missions",
            2,
            "missions_start_mission",
            "Creates a mission on an analyzed posting from one to three chosen requirements.",
            untrusted=_TEXT,
        ),
        McpAction(
            "PATCH /missions/{mission_id}/criteria/{index}",
            2,
            "missions_update_criterion",
            "Records the number of passed cases and the chosen note for a criterion.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /missions/{mission_id}/submission",
            2,
            "missions_submit_mission",
            "Privately records the submission and its proof once every case has passed.",
            untrusted=_TEXT,
        ),
    ),
)
