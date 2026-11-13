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

/** Bornes du contrat : travail de 10 à 120 minutes, pause de 0 à 60. */
export const WORK_RANGE = { min: 10, max: 120 } as const;
export const BREAK_RANGE = { min: 0, max: 60 } as const;

/** Les réglages d'étude tels que les édite la page : les nombres restent du texte pendant la saisie. */
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

/** Les réglages du serveur vers le brouillon (valeurs par défaut du back si absentes). */
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

/** Quels champs sont hors des bornes du contrat ; rien n'est envoyé tant qu'un champ l'est. */
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
 * Corps du `PUT /settings` après une modification de l'étude : tous les autres réglages (niveaux,
 * recherche, disponibilités…) sont repris tels quels de `current`, jamais écrasés.
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

/** Fuseaux proposés dans la liste (repli minimal si le navigateur ne sait pas les lister). */
const FALLBACK_ZONES = ["Europe/Paris", "Europe/London", "America/New_York", "Asia/Tokyo", "UTC"];

/**
 * Les fuseaux IANA que connaît le navigateur (`Intl.supportedValuesOf`), avec le fuseau actuel
 * même s'il n'y figure pas (UTC, ancien nom) : le choix enregistré n'est jamais perdu.
 */
export function timezoneChoices(current: string): string[] {
  const supported = (Intl as { supportedValuesOf?: (key: string) => string[] }).supportedValuesOf;
  const zones = supported ? supported("timeZone") : FALLBACK_ZONES;
  return zones.includes(current) || current === "" ? zones : [current, ...zones];
}
