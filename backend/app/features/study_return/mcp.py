from app.mcp.base import FeatureMcp, McpAction

_TEXT = ("plan.skills[].name", "plan.cards[].front", "plan.cards[].skill", "plan.last_block.title")

MCP = FeatureMcp(
    feature="study_return",
    actions=(
        McpAction(
            "GET /study-return",
            1,
            "study_return_get_plan",
            "Reads the account's comeback markers and its local reminder.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /study-return/prepare",
            2,
            "study_return_prepare_plan",
            "Picks a short path based on acquired skills, the due queue and the last block.",
            untrusted=_TEXT,
        ),
        McpAction(
            "PUT /study-return/reminder",
            2,
            "study_return_schedule_reminder",
            "Schedules a local comeback reminder on a chosen date, or removes it with null.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /study-return/start",
            2,
            "study_return_start_block",
            "Opens or resumes the comeback training without changing the program's tasks.",
            untrusted=_TEXT,
        ),
    ),
)
