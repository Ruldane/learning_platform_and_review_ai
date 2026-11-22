from app.mcp.base import FeatureMcp, McpAction

_NOTICE_TEXT = tuple(
    f"notices[].{key}" for key in ("title", "version", "intention", "indicator", "unit")
)


MCP = FeatureMcp(
    feature="routines",
    actions=(
        McpAction("GET /routines", 1, "routines_rules_list", "Liste les routines du compte."),
        McpAction(
            "POST /routines", 2, "routines_rule_create", "Enregistre une routine quotidienne."
        ),
        McpAction(
            "PATCH /routines/{routine_id}",
            2,
            "routines_rule_update",
            "Modifie une routine du compte.",
        ),
        McpAction(
            "GET /routines/{routine_id}/executions",
            1,
            "routines_executions_list",
            "Relit les exécutions de la routine.",
            untrusted=tuple(f"[].{field}" for field in _NOTICE_TEXT),
        ),
        McpAction(
            "POST /routines/{routine_id}/executions",
            2,
            "routines_execution_start",
            "Exécute la routine avec un reçu.",
            untrusted=_NOTICE_TEXT,
        ),
    ),
)
