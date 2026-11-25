"""MCP declaration for `gap`: the gap between January's profile and an offer."""

from app.mcp.base import FeatureMcp, McpAction, McpGraph

MCP = FeatureMcp(
    feature="gap",
    actions=(
        McpAction(
            "GET /postings/{posting_id}/gap",
            1,
            "gap_get_gap",
            "A posting's gap table (recomputed on every read).",
        ),
        McpAction(
            "POST /postings/{posting_id}/gap/plan",
            2,
            "gap_plan_missing_skills",
            "Proposes adding checked 'To add' or 'Out of scope' rows (`skills`) to the chosen "
            "validated program (`program_id`, the most recent by default). "
            "January validates the proposal before anything is written to the calendar.",
        ),
        McpAction(
            "POST /postings/{posting_id}/gap/validate",
            2,
            "gap_validate_skills",
            "'I already master them': adds a 'Validate my skills' module (`skills`) and "
            "launches its quiz; January takes it to get these skills validated.",
        ),
        McpAction(
            "GET /gap/top-missing",
            1,
            "gap_list_top_missing",
            "The 10 missing skills requested by the most postings.",
        ),
    ),
    graphs=(
        McpGraph(
            "gap_analysis",
            follow_only=True,
            summary="Analyzes the gap between a posting (`posting_id`) and January's profile.",
        ),
    ),
)
