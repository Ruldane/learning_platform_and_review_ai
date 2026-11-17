import { readTiers } from "./tierChoices";
import type { SettingsOut, UserSettings } from "./types";
import { buildUserSettings } from "./userSettings";

/** Les réglages de disponibilité et de rythme tels que les édite la page : des textes pendant la saisie. */
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

/** Les champs que `PUT /settings` peut refuser, pour y attacher l'erreur sans citer la valeur. */
export type AvailabilityField = keyof AvailabilityDraft;

export type AvailabilityErrors = Record<AvailabilityField | "weekendOrder", boolean>;

/** Bornes du contrat. */
export const MINUTES_RANGE = { min: 0, max: 1440 } as const;
export const DELAY_RANGE = { min: 1, max: 90 } as const;
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

/** Les réglages du serveur vers le brouillon (valeurs par défaut du back si absentes). */
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

/** Trois nombres de jours entiers, de 1 à 90, strictement croissants. */
export function delaysInvalid(delays: readonly string[]): boolean {
  const days = delays.map(whole);
  if (days.length !== 3 || days.some((day) => day === null)) return true;
  const [a, b, c] = days as [number, number, number];
  return (
    ![a, b, c].every((day) => day >= DELAY_RANGE.min && day <= DELAY_RANGE.max) || !(a < b && b < c)
  );
}

/** Quels champs sont hors des bornes du contrat ; rien n'est envoyé tant qu'un champ l'est. */
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

/** Budget hebdomadaire (minutes) : cinq jours de semaine plus le bloc de week-end le plus long ; `null` si une durée est invalide. */
export function weeklyBudget(draft: AvailabilityDraft): number | null {
  const weekday = within(draft.weekday, MINUTES_RANGE) ? whole(draft.weekday) : null;
  const weekend = within(draft.weekendMax, MINUTES_RANGE) ? whole(draft.weekendMax) : null;
  return weekday === null || weekend === null ? null : 5 * weekday + weekend;
}

/**
 * Corps du `PUT /settings` après une modification de la disponibilité : tous les autres réglages
 * (niveaux, recherche, surcharges, premier lancement…) sont repris tels quels de `current`.
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

/** Le brouillon `AvailabilityDraft` vers les noms de champs du contrat refusés par le serveur. */
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
