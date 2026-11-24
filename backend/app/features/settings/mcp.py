"""Déclaration MCP de `settings` : les préférences de January, jamais le niveau 4 (clés d'API,
modèles par niveau, surcharges par agent). `PUT /settings` brut porte aussi les modèles : il n'est
exposé que par l'action `settings_update_preferences`, qui lit l'objet (`merge_from`), ne change
que `PREFERENCE_FIELDS` (`body_fields`) et réécrit le tout."""

from app.mcp.base import FeatureMcp, McpAction, McpExclusion

# Niveau 4 : jamais écrits par le MCP.
PROTECTED_FIELDS = frozenset({"tiers", "agent_overrides"})

# Tout le reste : disponibilité, rythme, étude, style, recherche, fuseau…
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
