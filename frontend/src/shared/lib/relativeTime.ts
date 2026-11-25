import { t } from "@/shared/i18n/t";

const FULL = new Intl.DateTimeFormat("en-GB", { dateStyle: "long", timeStyle: "short" });
const DATE = new Intl.DateTimeFormat("en-GB", { dateStyle: "long", timeZone: "UTC" });
const CLOCK = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit" });

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** « il y a 5 min », « il y a 3 h »; « à l'instant » under one minute (or in the future). */
export function relativeTime(iso: string, now: Date = new Date()): string {
  const at = new Date(iso).getTime();
  if (Number.isNaN(at)) return iso;
  const elapsed = now.getTime() - at;
  if (elapsed < MINUTE) return t("time.now");
  if (elapsed < HOUR) return t("time.minutes", { count: Math.floor(elapsed / MINUTE) });
  if (elapsed < DAY) return t("time.hours", { count: Math.floor(elapsed / HOUR) });
  return t("time.days", { count: Math.floor(elapsed / DAY) });
}

/** « 16 novembre 2026 à 10:05 »: the full date of an instant, in the device's time zone. */
export function fullDateTime(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : FULL.format(date);
}

/** « 10 novembre 2026 »: a day (or instant) read in UTC, never shifted by the device's zone. */
export function longDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : DATE.format(date);
}

/** « 07:00 »: the time of an instant, in the device's time zone. */
export function clockTime(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : CLOCK.format(date);
}
