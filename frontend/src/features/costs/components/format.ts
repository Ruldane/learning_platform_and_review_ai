import { parseDay } from "@/shared/lib/format";

export { formatUsd } from "@/shared/lib/format";

const INTEGER = new Intl.NumberFormat("en-GB");
const TICKS = new Intl.NumberFormat("en-GB", {
  style: "currency",
  currency: "USD",
  currencyDisplay: "narrowSymbol",
  minimumFractionDigits: 2,
  maximumFractionDigits: 6,
});
const SECONDS = new Intl.NumberFormat("en-GB", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
const DAY_MONTH = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  timeZone: "UTC",
});
const CALL_TIME = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});
const CALL_TIME_YEAR = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

/** Groups thousands using a comma, as in 12,340. */
export const formatCount = (value: number): string => INTEGER.format(value);

/** Uses up to six decimal places so low-cost chart ticks can stay distinct. */
export const formatUsdTick = (usd: number): string => TICKS.format(usd);

/** « 340 ms » sous la seconde, « 1,8 s » au-delà. */
export function formatLatency(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${SECONDS.format(ms / 1000)} s`;
}

/** « 16 nov. » : un jour `AAAA-MM-JJ` pour l'axe du graphique. */
export const dayMonth = (iso: string): string => DAY_MONTH.format(parseDay(iso));

/**
 * « 16 nov., 10:30 » : l'instant d'un appel, à l'heure du poste ; l'année si ce n'est pas l'année
 * en cours.
 */
export function formatCallTime(iso: string): string {
  const at = new Date(iso);
  const format = at.getFullYear() === new Date().getFullYear() ? CALL_TIME : CALL_TIME_YEAR;
  return format.format(at);
}
