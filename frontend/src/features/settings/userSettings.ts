import { readTiers } from "./tierChoices";
import type {
  BraveUsageOut,
  BraveUsageView,
  ModelChoice,
  SearchSettingsView,
  SettingsOut,
  TierChoices,
  UserSettings,
} from "./types";

/**
 * Every field of `T` is written (even those the contract leaves optional), value or
 * `undefined`.
 */
type EveryField<T> = { [K in keyof Required<T>]: T[K] };

/**
 * Body of `PUT /settings`: full replacement. The fields of `UserSettings` are picked one by one
 * (never `...settings`): `vision_enabled` and `weekly_budget_minutes` are computed by the
 * back end and are not part of the write contract.
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
    onboarding_done: current.onboarding_done,
    preferred_domains: current.preferred_domains,
    radar_role: current.radar_role,
    radar_zone: current.radar_zone,
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
    // A field added to the contract and forgotten here no longer compiles (focus n° 5).
  } satisfies EveryField<UserSettings>;
}

/**
 * Search settings as the components edit them (back-end defaults when missing).
 * absents).
 */
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
 * Body of `PUT /settings` after a search change: all the other settings
 * (levels, availability, review…) are copied as-is from `current`, never overwritten.
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

/** `GET /research/usage` to the Brave gauge (`month`: « AAAA-MM », in UTC, as the contract). */
export function toBraveUsageView({ brave }: { brave: BraveUsageOut }): BraveUsageView {
  return { hasKey: brave.has_key, used: brave.used, cap: brave.cap, month: brave.month };
}

/**
 * Body of `PUT /settings` after a style guide change: all the other settings
 * are copied as-is from `current`.
 */
export function withStyleGuide(current: SettingsOut, styleGuide: string): UserSettings {
  return { ...buildUserSettings(current, readTiers(current.tiers)), style_guide: styleGuide };
}

/**
 * Body of `PUT /settings` after several agent model choices at once (`changes`: the agent
 * to its model, or `null` to return it to its level): the other overrides and all the
 * other settings are kept.
 */
export function withAgentOverrides(
  current: SettingsOut,
  changes: Record<string, ModelChoice | null>,
): UserSettings {
  const overrides = { ...current.agent_overrides };
  for (const [agent, choice] of Object.entries(changes)) {
    if (choice) overrides[agent] = choice;
    else delete overrides[agent];
  }
  return { ...buildUserSettings(current, readTiers(current.tiers)), agent_overrides: overrides };
}

/**
 * Body of `PUT /settings` after choosing a model for an agent (`choice`), or its return to its
 * niveau (`null`).
 */
export function withAgentOverride(
  current: SettingsOut,
  agent: string,
  choice: ModelChoice | null,
): UserSettings {
  return withAgentOverrides(current, { [agent]: choice });
}
