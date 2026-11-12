import { parseDay } from "@/shared/lib/format";

const WEEKDAY = new Intl.DateTimeFormat("fr-FR", { weekday: "short", timeZone: "UTC" });
const DAY_OF_MONTH = new Intl.DateTimeFormat("fr-FR", { day: "numeric", timeZone: "UTC" });

/** « lun. » : titre de colonne. */
export function weekdayLabel(iso: string): string {
  return WEEKDAY.format(parseDay(iso));
}

/** « 16 » : numéro du jour dans le mois. */
export function dayOfMonth(iso: string): string {
  return DAY_OF_MONTH.format(parseDay(iso));
}

export function dayLoad(tasks: { minutes: number }[]): number {
  return tasks.reduce((sum, task) => sum + task.minutes, 0);
}
