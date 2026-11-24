import { parseDay } from "@/shared/lib/format";

const INTEGER = new Intl.NumberFormat("en-GB");
const CENTS = new Intl.NumberFormat("en-GB", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const MILLS = new Intl.NumberFormat("en-GB", {
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
});
const TICKS = new Intl.NumberFormat("en-GB", {
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

/** « 12 340 » (espace insécable fine entre les milliers). */
export const formatCount = (value: number): string => INTEGER.format(value);

/**
 * « 0,42 $ » (espace insécable) ; trois décimales sous le centime, et « < 0,001 $ » sous le
 * millième : un coût non nul ne s'écrit jamais « 0,00 $ » ni « 0,000 $ ».
 */
export function formatUsd(usd: number): string {
  if (usd > 0 && usd < 0.001) return "< 0,001\u00a0$";
  const digits = usd > 0 && usd < 0.01 ? MILLS : CENTS;
  return `${digits.format(usd)}\u00a0$`;
}

/**
 * Une graduation de l'axe des coûts : deux décimales au moins, jusqu'à six pour qu'une fenêtre où
 * chaque jour coûte moins d'un millième garde des graduations toutes différentes (« 0,0004 $ »).
 */
export const formatUsdTick = (usd: number): string => `${TICKS.format(usd)}\u00a0$`;

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
