const DAY = /^(\d{4})-(\d{2})-(\d{2})$/;
const INSTANT = new Intl.DateTimeFormat("en-GB", { dateStyle: "short", timeStyle: "short" });
const NUMBER = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 1 });

/** « 03/11/2026 » : un jour `AAAA-MM-JJ`, lu tel quel (jamais décalé par le fuseau). */
export function formatDay(day: string): string {
  const match = DAY.exec(day);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : day;
}

/** « 03/11/2026 14:30 » : un instant ISO ; un texte illisible est rendu tel quel. */
export function formatInstant(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : INSTANT.format(date);
}

/** « 12 % » : une part entre 0 et 1. */
export function formatPercent(share: number): string {
  return `${Math.round(share * 100)} %`;
}

/** « 4,5 » : un nombre à une décimale au plus, virgule française. */
export function formatNumber(value: number): string {
  return NUMBER.format(value);
}

/** Le jour `AAAA-MM-JJ` de `now` dans le fuseau de l'appareil (jamais décalé par l'UTC). */
export function todayString(now: Date = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}
