import { DELAY_RANGE, MINUTES_RANGE } from "./components/ranges";
import { readTiers } from "./tierChoices";
import type { SettingsOut, UserSettings } from "./types";
import { buildUserSettings } from "./userSettings";

/**
 * Availability and pace settings, as the page edits them: text while the user types;
 * saisie.
 */
export interface AvailabilityDraft {
  weekday: string;
  weekendMin: string;
  weekendMax: string;
  /** `HH:MM`. */
  briefTime: string;
  delays: [string, string, string];
  rounds: string;
  tokenCap: string;
  lessonLanguage: string;
}

/** Fields `PUT /settings` may reject, so the error attaches without quoting the value. */
export type AvailabilityField = keyof AvailabilityDraft;

export type AvailabilityErrors = Record<AvailabilityField | "weekendOrder", boolean>;

/** Contract bounds. */
export { DELAY_RANGE, MINUTES_RANGE };
export const ROUNDS_RANGE = { min: 1, max: 5 } as const;
export const TOKEN_CAP_MIN = 10_000;

const TIME_PATTERN = /^([01]\d|2[0-3]):[0-5]\d$/;

const whole = (text: string): number | null => {
  const value = Number(text);
  return text.trim() !== "" && Number.isInteger(value) ? value : null;
};

const within = (text: string, range: { min: number; max: number }): boolean => {
  const value = whole(text);
  return value !== null && value >= range.min && value <= range.max;
};

/** Server settings for the draft (back-end defaults when missing). */
export function toAvailabilityDraft(settings: SettingsOut): AvailabilityDraft {
  const { availability: a } = settings;
  const delays = settings.reminder_delays_days ?? [7, 14, 21];
  return {
    weekday: String(a?.weekday_minutes ?? 120),
    weekendMin: String(a?.weekend_block_min_minutes ?? 180),
    weekendMax: String(a?.weekend_block_max_minutes ?? 240),
    briefTime: settings.brief_time,
    delays: [String(delays[0] ?? 7), String(delays[1] ?? 14), String(delays[2] ?? 21)],
    rounds: String(settings.debate_rounds),
    tokenCap: String(settings.session_token_cap),
    lessonLanguage: settings.lesson_language,
  };
}

/** Three whole-day numbers, from 1 to 90, strictly increasing. */
export function delaysInvalid(delays: readonly string[]): boolean {
  const days = delays.map(whole);
  if (days.length !== 3 || days.some((day) => day === null)) return true;
  const [a, b, c] = days as [number, number, number];
  return (
    ![a, b, c].every((day) => day >= DELAY_RANGE.min && day <= DELAY_RANGE.max) || !(a < b && b < c)
  );
}

/** Which fields are outside the contract bounds; nothing is sent while one is. */
export function availabilityErrors(draft: AvailabilityDraft): AvailabilityErrors {
  const min = whole(draft.weekendMin);
  const max = whole(draft.weekendMax);
  const order = min !== null && max !== null && min > max;
  return {
    weekday: !within(draft.weekday, MINUTES_RANGE),
    weekendMin: !within(draft.weekendMin, MINUTES_RANGE) || order,
    weekendMax: !within(draft.weekendMax, MINUTES_RANGE) || order,
    weekendOrder: order,
    briefTime: !TIME_PATTERN.test(draft.briefTime),
    delays: delaysInvalid(draft.delays),
    rounds: !within(draft.rounds, ROUNDS_RANGE),
    tokenCap: (whole(draft.tokenCap) ?? 0) < TOKEN_CAP_MIN,
    lessonLanguage: draft.lessonLanguage === "",
  };
}

export const hasAvailabilityErrors = (errors: AvailabilityErrors): boolean =>
  Object.values(errors).some(Boolean);

export const sameAvailabilityDraft = (a: AvailabilityDraft, b: AvailabilityDraft): boolean =>
  JSON.stringify(a) === JSON.stringify(b);

/**
 * Weekly budget (minutes): five weekdays plus the longest weekend block;
 * `null` if a duration is invalid.
 */
export function weeklyBudget(draft: AvailabilityDraft): number | null {
  const weekday = within(draft.weekday, MINUTES_RANGE) ? whole(draft.weekday) : null;
  const weekend = within(draft.weekendMax, MINUTES_RANGE) ? whole(draft.weekendMax) : null;
  return weekday === null || weekend === null ? null : 5 * weekday + weekend;
}

/**
 * Body of `PUT /settings` after an availability change: all other settings
 * (levels, search, overrides, first run…) are copied as-is from `current`.
 */
export function withAvailabilitySettings(
  current: SettingsOut,
  draft: AvailabilityDraft,
): UserSettings {
  return {
    ...buildUserSettings(current, readTiers(current.tiers)),
    availability: {
      weekday_minutes: Number(draft.weekday),
      weekend_block_min_minutes: Number(draft.weekendMin),
      weekend_block_max_minutes: Number(draft.weekendMax),
    },
    brief_time: draft.briefTime,
    reminder_delays_days: draft.delays.map(Number),
    debate_rounds: Number(draft.rounds),
    session_token_cap: Number(draft.tokenCap),
    lesson_language: draft.lessonLanguage,
  };
}

/** Maps the `AvailabilityDraft` to the contract field names the server rejected. */
export const CONTRACT_FIELDS: Record<AvailabilityField, string> = {
  weekday: "availability.weekday_minutes",
  weekendMin: "availability.weekend_block_min_minutes",
  weekendMax: "availability.weekend_block_max_minutes",
  briefTime: "brief_time",
  delays: "reminder_delays_days",
  rounds: "debate_rounds",
  tokenCap: "session_token_cap",
  lessonLanguage: "lesson_language",
};
