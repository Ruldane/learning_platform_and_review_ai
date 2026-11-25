import { readTiers } from "./tierChoices";
import type { SettingsOut, UserSettings } from "./types";
import { buildUserSettings } from "./userSettings";

export const WEEKDAYS = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
] as const;

export type Weekday = (typeof WEEKDAYS)[number];

/** Contract bounds: work from 10 to 120 minutes, break from 0 to 60. */
export const WORK_RANGE = { min: 10, max: 120 } as const;
export const BREAK_RANGE = { min: 0, max: 60 } as const;

/** The study settings as the page edits them: the numbers stay text while typing. */
export interface StudyDraft {
  work: string;
  pause: string;
  day: Weekday;
  /** `HH:MM`. */
  time: string;
  /** Fuseau IANA (ex. `Europe/Paris`). */
  zone: string;
}

export interface StudyDraftErrors {
  work: boolean;
  pause: boolean;
  time: boolean;
  zone: boolean;
}

const TIME_PATTERN = /^([01]\d|2[0-3]):[0-5]\d$/;

/** Server settings to the draft (back-end defaults when missing). */
export function toStudyDraft(settings: SettingsOut): StudyDraft {
  return {
    work: String(settings.study_work_minutes),
    pause: String(settings.study_break_minutes),
    day: settings.weekly_review?.day ?? "sunday",
    time: settings.weekly_review?.time ?? "18:00",
    zone: settings.timezone,
  };
}

const wholeBetween = (text: string, range: { min: number; max: number }): boolean => {
  const value = Number(text);
  return text.trim() !== "" && Number.isInteger(value) && value >= range.min && value <= range.max;
};

/** Which fields are outside the contract bounds; nothing is sent while one is. */
export function studyDraftErrors(draft: StudyDraft): StudyDraftErrors {
  return {
    work: !wholeBetween(draft.work, WORK_RANGE),
    pause: !wholeBetween(draft.pause, BREAK_RANGE),
    time: !TIME_PATTERN.test(draft.time),
    zone: draft.zone === "",
  };
}

export const hasStudyErrors = (errors: StudyDraftErrors): boolean =>
  Object.values(errors).some(Boolean);

export const sameStudyDraft = (a: StudyDraft, b: StudyDraft): boolean =>
  JSON.stringify(a) === JSON.stringify(b);

/**
 * Body of `PUT /settings` after a study change: all the other settings (levels,
 * search, availability…) are copied as-is from `current`, never overwritten.
 */
export function withStudySettings(current: SettingsOut, draft: StudyDraft): UserSettings {
  return {
    ...buildUserSettings(current, readTiers(current.tiers)),
    study_work_minutes: Number(draft.work),
    study_break_minutes: Number(draft.pause),
    weekly_review: { day: draft.day, time: draft.time },
    timezone: draft.zone,
  };
}

/** Time zones offered in the list (minimal fallback if the browser cannot list them). */
const FALLBACK_ZONES = ["Europe/Paris", "Europe/London", "America/New_York", "Asia/Tokyo", "UTC"];

/**
 * The IANA time zones the browser knows (`Intl.supportedValuesOf`), plus the current zone
 * even if it is not among them (UTC, old name): the saved choice is never lost.
 */
export function timezoneChoices(current: string): string[] {
  const supported = (Intl as { supportedValuesOf?: (key: string) => string[] }).supportedValuesOf;
  const zones = supported ? supported("timeZone") : FALLBACK_ZONES;
  return zones.includes(current) || current === "" ? zones : [current, ...zones];
}
