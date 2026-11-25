const SHORT = new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "2-digit" });

/** « 03/11 »: the day and month of an ISO instant; an unreadable date is returned as is. */
export function shortDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : SHORT.format(date);
}
