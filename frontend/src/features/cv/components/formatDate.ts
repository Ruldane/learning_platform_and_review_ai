const DAY = new Intl.DateTimeFormat("en-GB", { dateStyle: "short" });

/** « 03/11/2026 » : le jour d'un instant ISO ; une date illisible est rendue telle quelle. */
export function formatDay(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : DAY.format(date);
}
