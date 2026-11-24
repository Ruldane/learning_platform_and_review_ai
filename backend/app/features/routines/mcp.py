from app.mcp.base import FeatureMcp, McpAction

_NOTICE_TEXT = tuple(
    f"notices[].{key}" for key in ("title", "version", "intention", "indicator", "unit")
)


MCP = FeatureMcp(
    feature="routines",
    actions=(
        McpAction("GET /routines", 1, "routines_rules_list", "Lists the account's routines."),
        McpAction("POST /routines", 2, "routines_rule_create", "Saves a daily routine."),
        McpAction(
            "PATCH /routines/{routine_id}",
            2,
            "routines_rule_update",
            "Edits one of the account's routines.",
        ),
        McpAction(
            "GET /routines/{routine_id}/executions",
            1,
            "routines_executions_list",
            "Reads the routine's executions.",
            untrusted=tuple(f"[].{field}" for field in _NOTICE_TEXT),
        ),
        McpAction(
            "POST /routines/{routine_id}/executions",
            2,
            "routines_execution_start",
            "Runs the routine with a receipt.",
            untrusted=_NOTICE_TEXT,
        ),
    ),
)
