const DAY = new Intl.DateTimeFormat("en-GB", { dateStyle: "short" });

/** « 03/11/2026 »: the day of an ISO instant; an unreadable date is returned as is. */
export function formatDay(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : DAY.format(date);
}
