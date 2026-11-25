import { parseDay } from "@/shared/lib/format";

const WEEKDAY = new Intl.DateTimeFormat("en-GB", { weekday: "short", timeZone: "UTC" });
const DAY_OF_MONTH = new Intl.DateTimeFormat("en-GB", { day: "numeric", timeZone: "UTC" });

/** « lun. »: column header. */
export function weekdayLabel(iso: string): string {
  return WEEKDAY.format(parseDay(iso));
}

/** « 16 »: day number in the month. */
export function dayOfMonth(iso: string): string {
  return DAY_OF_MONTH.format(parseDay(iso));
}

export function dayLoad(tasks: { minutes: number }[]): number {
  return tasks.reduce((sum, task) => sum + task.minutes, 0);
}
