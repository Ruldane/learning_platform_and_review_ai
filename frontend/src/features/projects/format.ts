const DAY = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long" });
const INSTANT = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long", timeStyle: "short" });

/** « 16 novembre 2026 » : le jour d'un instant ISO. */
export const formatDay = (iso: string): string => DAY.format(new Date(iso));

/** « 16 novembre 2026 à 10:30 » : un instant ISO au jour et à l'heure. */
export const formatInstant = (iso: string): string => INSTANT.format(new Date(iso));
