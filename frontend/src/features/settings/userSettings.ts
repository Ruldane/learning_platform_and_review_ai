import type { SettingsOut, TierChoices, UserSettings } from "./types";

/**
 * Corps du `PUT /settings` : remplacement complet. On choisit un à un les champs de `UserSettings`
 * (jamais de `...settings`) : `vision_enabled` et `weekly_budget_minutes` sont calculés par le
 * back et ne font pas partie du contrat d'écriture.
 */
export function buildUserSettings(current: SettingsOut, tiers: TierChoices): UserSettings {
  const { availability } = current;
  return {
    agent_overrides: current.agent_overrides,
    availability: availability && {
      weekday_minutes: availability.weekday_minutes,
      weekend_block_min_minutes: availability.weekend_block_min_minutes,
      weekend_block_max_minutes: availability.weekend_block_max_minutes,
    },
    brief_time: current.brief_time,
    debate_rounds: current.debate_rounds,
    excluded_domains: current.excluded_domains,
    lesson_language: current.lesson_language,
    preferred_domains: current.preferred_domains,
    reminder_delays_days: current.reminder_delays_days,
    search_languages: current.search_languages,
    search_max_pages: current.search_max_pages,
    search_max_queries: current.search_max_queries,
    search_provider_order: current.search_provider_order,
    session_token_cap: current.session_token_cap,
    style_guide: current.style_guide,
    tiers,
    weekly_review: current.weekly_review,
  };
}
