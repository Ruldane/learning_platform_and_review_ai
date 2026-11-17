"""Déclaration MCP de `settings` : les préférences de January, jamais le niveau 4 (clés d'API,
modèles par niveau, surcharges par agent). `PUT /settings` brut porte aussi les modèles : il n'est
exposé que par l'action `settings_update_preferences`, qui lit l'objet (`merge_from`), ne change
que `PREFERENCE_FIELDS` (`body_fields`) et réécrit le tout."""

from app.mcp.base import FeatureMcp, McpAction

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

_SECRETS = (
    "Clés d'API, modèles par niveau et surcharges par agent : niveau 4, jamais exposé au MCP."
)

MCP = FeatureMcp(
    feature="settings",
    actions=(
        McpAction(
            "GET /settings",
            1,
            "settings_get_preferences",
            "Les préférences de January (disponibilité, rythme, étude, style, recherche, "
            "fuseau). Jamais les modèles par niveau, les surcharges par agent ni les clés.",
            response_fields=PREFERENCE_FIELDS,
        ),
        McpAction(
            "PUT /settings",
            2,
            "settings_update_preferences",
            "Change des préférences : n'envoie que les champs à modifier, les autres sont "
            "gardés. Les modèles et les clés ne se changent pas ici.",
            body_fields=PREFERENCE_FIELDS,
            merge_from="GET /settings",
        ),
    ),
    excluded={
        "GET /settings/api-keys": _SECRETS,
        "POST /settings/api-keys": _SECRETS,
        "DELETE /settings/api-keys/{provider}": _SECRETS,
        "POST /settings/api-keys/{provider}/test": _SECRETS,
        "GET /settings/models": _SECRETS,
        "GET /settings/agents": _SECRETS,
    },
)
