const LONG_DAY = new Intl.DateTimeFormat("fr-FR", {
  weekday: "long",
  day: "numeric",
  month: "long",
  timeZone: "UTC",
});
const SHORT_DAY = new Intl.DateTimeFormat("fr-FR", {
  weekday: "short",
  day: "numeric",
  month: "short",
  timeZone: "UTC",
});

/** Un jour `AAAA-MM-JJ` lu comme minuit UTC : le fuseau du poste ne décale jamais le jour. */
export function parseDay(iso: string): Date {
  return new Date(`${iso}T00:00:00Z`);
}

/** « mercredi 18 novembre » : nomme un jour en toutes lettres. */
export function longDay(iso: string): string {
  return LONG_DAY.format(parseDay(iso));
}

/** « lun. 16 nov. » : forme courte, pour les comparaisons. */
export function shortDay(iso: string): string {
  return SHORT_DAY.format(parseDay(iso));
}

/** « 11 h 30 », « 2 h » ou « 45 min ». */
export function formatMinutes(total: number): string {
  const minutes = Math.max(0, Math.round(total));
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours === 0) return `${rest} min`;
  return rest === 0 ? `${hours} h` : `${hours} h ${String(rest).padStart(2, "0")}`;
}
