"""Ton futur toi en lecture seule au niveau 1."""

from app.mcp.base import FeatureMcp, McpAction

MCP = FeatureMcp(
    feature="future_self",
    actions=(
        McpAction(
            "GET /future-self",
            1,
            "future_self_get_projection",
            "Compares study paces for a role (`role`), an area (`zone`) and a validated program "
            "(`program_id`). `alternative_weekly_minutes` simulates another weekly availability. "
            "`target_percent` sets the targeted share of postings (60 by default).",
            untrusted=("recommendations[].chapter.title", "recommendations[].chapter.skills[]"),
        ),
    ),
)
