const DAY = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" });
const DAY_TIME = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" });

function parse(iso: string): Date | null {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** Readable date (« 11 nov. 2026 »); an unreadable date is shown as is. */
export function formatDay(iso: string): string {
  const date = parse(iso);
  return date ? DAY.format(date) : iso;
}

/** Readable date and time, for the write log. */
export function formatDayTime(iso: string): string {
  const date = parse(iso);
  return date ? DAY_TIME.format(date) : iso;
}
