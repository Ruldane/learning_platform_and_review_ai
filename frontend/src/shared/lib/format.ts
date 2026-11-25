const LONG_DAY = new Intl.DateTimeFormat("en-GB", {
  weekday: "long",
  day: "numeric",
  month: "long",
  timeZone: "UTC",
});
const SHORT_DAY = new Intl.DateTimeFormat("en-GB", {
  weekday: "short",
  day: "numeric",
  month: "short",
  timeZone: "UTC",
});

const USD = { style: "currency", currency: "USD", currencyDisplay: "narrowSymbol" } as const;
const DOLLARS_AND_CENTS = new Intl.NumberFormat("en-GB", USD);
const DOLLARS_AND_MILLS = new Intl.NumberFormat("en-GB", {
  ...USD,
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
});

/** Keeps small positive costs visible below one cent. */
export function formatUsd(usd: number): string {
  if (usd > 0 && usd < 0.001) return `< ${DOLLARS_AND_MILLS.format(0.001)}`;
  const format = usd > 0 && usd < 0.01 ? DOLLARS_AND_MILLS : DOLLARS_AND_CENTS;
  return format.format(usd);
}

/** A `YYYY-MM-DD` day read as UTC midnight: the device's time zone never shifts the day. */
export function parseDay(iso: string): Date {
  return new Date(`${iso}T00:00:00Z`);
}

/** Example: « mercredi 18 novembre », the day named in full. */
export function longDay(iso: string): string {
  return LONG_DAY.format(parseDay(iso));
}

/** Example: « lun. 16 nov. », short form for comparisons. */
export function shortDay(iso: string): string {
  return SHORT_DAY.format(parseDay(iso));
}

/** Examples: « 11 h 30 », « 2 h » or « 45 min ». */
export function formatMinutes(total: number): string {
  const minutes = Math.max(0, Math.round(total));
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours === 0) return `${rest} min`;
  return rest === 0 ? `${hours} h` : `${hours} h ${String(rest).padStart(2, "0")}`;
}

/** The `YYYY-MM-DD` day of an instant, in the device's time zone (today by default). */
export function localDay(at: Date = new Date()): string {
  const month = String(at.getMonth() + 1).padStart(2, "0");
  const day = String(at.getDate()).padStart(2, "0");
  return `${at.getFullYear()}-${month}-${day}`;
}

/** The `YYYY-MM-DD` day `days` days after `iso` (computed in UTC: no DST jump). */
export function addDays(iso: string, days: number): string {
  const date = parseDay(iso);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}
