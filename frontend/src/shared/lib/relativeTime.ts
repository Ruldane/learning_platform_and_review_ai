import { t } from "@/shared/i18n/t";

const FULL = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long", timeStyle: "short" });
const DATE = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long", timeZone: "UTC" });
const CLOCK = new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit" });

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** « il y a 5 min », « il y a 3 h », « il y a 2 j » ; « à l'instant » sous une minute (ou dans le futur). */
export function relativeTime(iso: string, now: Date = new Date()): string {
  const at = new Date(iso).getTime();
  if (Number.isNaN(at)) return iso;
  const elapsed = now.getTime() - at;
  if (elapsed < MINUTE) return t("time.now");
  if (elapsed < HOUR) return t("time.minutes", { count: Math.floor(elapsed / MINUTE) });
  if (elapsed < DAY) return t("time.hours", { count: Math.floor(elapsed / HOUR) });
  return t("time.days", { count: Math.floor(elapsed / DAY) });
}

/** « 16 novembre 2026 à 10:05 » : la date complète d'un instant, dans le fuseau du poste. */
export function fullDateTime(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : FULL.format(date);
}

/** « 10 novembre 2026 » : un jour (ou un instant) lu en UTC, jamais décalé par le fuseau du poste. */
export function longDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : DATE.format(date);
}

/** « 07:00 » : l'heure d'un instant, dans le fuseau du poste. */
export function clockTime(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : CLOCK.format(date);
}
