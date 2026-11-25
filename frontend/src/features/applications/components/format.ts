const DAY = /^(\d{4})-(\d{2})-(\d{2})$/;
const INSTANT = new Intl.DateTimeFormat("en-GB", { dateStyle: "short", timeStyle: "short" });
const NUMBER = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 1 });
const PERCENT = new Intl.NumberFormat("en-GB", { style: "percent", maximumFractionDigits: 0 });

/** Display a calendar date without shifting it for the device's time zone. */
export function formatDay(day: string): string {
  const match = DAY.exec(day);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : day;
}

/** Format an ISO timestamp in local time, retaining unreadable strings. */
export function formatInstant(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : INSTANT.format(date);
}

/** Display a fraction as a rounded percentage. */
export function formatPercent(share: number): string {
  return PERCENT.format(share);
}

/** Format a number with at most one decimal place. */
export function formatNumber(value: number): string {
  return NUMBER.format(value);
}

/** Return the calendar date of the given instant in the device's time zone. */
export function todayString(now: Date = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}
