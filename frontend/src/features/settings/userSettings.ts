import { readTiers } from "./tierChoices";
import type {
  BraveUsageOut,
  BraveUsageView,
  SearchSettingsView,
  SettingsOut,
  TierChoices,
  UserSettings,
} from "./types";

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
    study_break_minutes: current.study_break_minutes,
    study_work_minutes: current.study_work_minutes,
    style_guide: current.style_guide,
    tiers,
    timezone: current.timezone,
    weekly_review: current.weekly_review,
  };
}

/** Les réglages de recherche tels que les éditent les composants (valeurs par défaut du back si absents). */
export function toSearchSettingsView(settings: SettingsOut): SearchSettingsView {
  return {
    languages: settings.search_languages ?? ["fr", "en"],
    preferred: settings.preferred_domains ?? [],
    excluded: settings.excluded_domains ?? [],
    order: settings.search_provider_order ?? ["searxng", "brave"],
    maxQueries: settings.search_max_queries,
    maxPages: settings.search_max_pages,
  };
}

/**
 * Corps du `PUT /settings` après une modification de la recherche : tous les autres réglages
 * (niveaux, disponibilités, revue…) sont repris tels quels de `current`, jamais écrasés.
 */
export function withSearchSettings(current: SettingsOut, search: SearchSettingsView): UserSettings {
  return {
    ...buildUserSettings(current, readTiers(current.tiers)),
    search_languages: search.languages,
    preferred_domains: search.preferred,
    excluded_domains: search.excluded,
    search_provider_order: search.order,
    search_max_queries: search.maxQueries,
    search_max_pages: search.maxPages,
  };
}

/** `GET /research/usage` vers la jauge Brave (`month` : « AAAA-MM », en UTC, comme le contrat). */
export function toBraveUsageView({ brave }: { brave: BraveUsageOut }): BraveUsageView {
  return { hasKey: brave.has_key, used: brave.used, cap: brave.cap, month: brave.month };
}
