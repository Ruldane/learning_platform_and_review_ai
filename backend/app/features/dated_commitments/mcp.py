from app.mcp.base import FeatureMcp, McpAction

_TEXT = ("title", "version", "intention", "indicator", "unit", "note")

MCP = FeatureMcp(
    feature="dated_commitments",
    actions=(
        McpAction(
            "GET /dated-commitments",
            1,
            "dated_commitments_list_entries",
            "Lists the account's dated decisions and the measurements already recorded.",
            untrusted=tuple(f"[].{field}" for field in _TEXT),
        ),
        McpAction(
            "GET /dated-commitments/{commitment_id}",
            1,
            "dated_commitments_read_entry",
            "Reads a decision, its version, its intention and its indicator.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /dated-commitments",
            2,
            "dated_commitments_plan_review",
            "Schedules the review of a decision with its version, its target and its date.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /dated-commitments/{commitment_id}/review",
            2,
            "dated_commitments_record_result",
            "Records the measurement observed at the due date and its gap to the target.",
            untrusted=_TEXT,
        ),
    ),
)
