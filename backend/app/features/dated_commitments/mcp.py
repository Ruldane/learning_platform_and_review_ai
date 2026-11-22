from app.mcp.base import FeatureMcp, McpAction

_TEXT = ("title", "version", "intention", "indicator", "unit", "note")

MCP = FeatureMcp(
    feature="dated_commitments",
    actions=(
        McpAction(
            "GET /dated-commitments",
            1,
            "dated_commitments_list_entries",
            "Liste les décisions datées du compte et les mesures déjà enregistrées.",
            untrusted=tuple(f"[].{field}" for field in _TEXT),
        ),
        McpAction(
            "GET /dated-commitments/{commitment_id}",
            1,
            "dated_commitments_read_entry",
            "Relit une décision, sa version, son intention et son indicateur.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /dated-commitments",
            2,
            "dated_commitments_plan_review",
            "Planifie le retour sur une décision avec sa version, sa cible et sa date.",
            untrusted=_TEXT,
        ),
        McpAction(
            "POST /dated-commitments/{commitment_id}/review",
            2,
            "dated_commitments_record_result",
            "Enregistre la mesure observée à l’échéance et calcule son écart à la cible.",
            untrusted=_TEXT,
        ),
    ),
)
