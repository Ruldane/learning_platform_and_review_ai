"""MCP declaration for `settings`: January's preferences, never level 4 (API keys, models per
level, per-agent overrides). The raw `PUT /settings` also carries the models: it is exposed only
through the `settings_update_preferences` action, which reads the object (`merge_from`), changes
only `PREFERENCE_FIELDS` (`body_fields`) and rewrites everything."""

from app.mcp.base import FeatureMcp, McpAction, McpExclusion

# Level 4: never written by the MCP.
PROTECTED_FIELDS = frozenset({"tiers", "agent_overrides"})

# Everything else: availability, pace, study, style, search, time zone…
PREFERENCE_FIELDS = frozenset(
    {
        "availability",
        "lesson_language",
        "search_languages",
        "debate_rounds",
        "session_token_cap",
        "brief_time",
        "weekly_review",
        "reminder_delays_days",
        "style_guide",
        "preferred_domains",
        "excluded_domains",
        "search_provider_order",
        "search_max_queries",
        "search_max_pages",
        "study_work_minutes",
        "study_break_minutes",
        "timezone",
        "radar_role",
        "radar_zone",
        "onboarding_done",
    }
)

_SECRETS = "API keys, models per tier and per-agent overrides: level 4, never exposed to MCP."

MCP = FeatureMcp(
    feature="settings",
    actions=(
        McpAction(
            "GET /settings",
            1,
            "settings_get_preferences",
            "January's preferences (availability, pace, study, style, search, "
            "time zone). Never the models per tier, the per-agent overrides or the keys.",
            response_fields=PREFERENCE_FIELDS,
        ),
        McpAction(
            "PUT /settings",
            2,
            "settings_update_preferences",
            "Changes preferences: send only the fields to modify, the others are "
            "kept. Models and keys cannot be changed here.",
            body_fields=PREFERENCE_FIELDS,
            merge_from="GET /settings",
            response_fields=PREFERENCE_FIELDS,
        ),
    ),
    excluded={
        "GET /settings/api-keys": McpExclusion.MODEL_SETTINGS,
        "POST /settings/api-keys": McpExclusion.MODEL_SETTINGS,
        "DELETE /settings/api-keys/{provider}": McpExclusion.MODEL_SETTINGS,
        "POST /settings/api-keys/{provider}/test": McpExclusion.MODEL_SETTINGS,
        "GET /settings/models": McpExclusion.MODEL_SETTINGS,
        "GET /settings/agents": McpExclusion.MODEL_SETTINGS,
    },
)
