from app.mcp.base import FeatureMcp, McpAction

_TEXT = ("plan.skills[].name", "plan.cards[].front", "plan.cards[].skill", "plan.last_block.title")

MCP = FeatureMcp(
    feature="study_return",
    actions=(
        McpAction(
            "GET /study-return",
            1,
            "study_return_get_plan",
            "Relit les repères de reprise du compte et son rappel local.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /study-return/prepare",
            2,
            "study_return_prepare_plan",
            "Choisit un parcours court d’après les acquis, la file due et le dernier bloc.",
            untrusted=_TEXT,
        ),
        McpAction(
            "PUT /study-return/reminder",
            2,
            "study_return_schedule_reminder",
            "Planifie un rappel local de reprise à une date choisie, ou le retire avec null.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /study-return/start",
            2,
            "study_return_start_block",
            "Ouvre ou reprend le training de reprise sans modifier les tâches du programme.",
            untrusted=_TEXT,
        ),
    ),
)
