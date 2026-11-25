const DAY = new Intl.DateTimeFormat("en-GB", { dateStyle: "long" });
const INSTANT = new Intl.DateTimeFormat("en-GB", { dateStyle: "long", timeStyle: "short" });

/** « 16 novembre 2026 »: the day of an ISO instant. */
export const formatDay = (iso: string): string => DAY.format(new Date(iso));

/** « 16 novembre 2026 à 10:30 »: an ISO instant at the day and time. */
export const formatInstant = (iso: string): string => INSTANT.format(new Date(iso));
