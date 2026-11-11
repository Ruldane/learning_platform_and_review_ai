const DAY = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" });
const DAY_TIME = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" });

function parse(iso: string): Date | null {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** Date lisible (« 11 nov. 2026 ») ; une date illisible est rendue telle quelle. */
export function formatDay(iso: string): string {
  const date = parse(iso);
  return date ? DAY.format(date) : iso;
}

/** Date et heure lisibles, pour le journal des écritures. */
export function formatDayTime(iso: string): string {
  const date = parse(iso);
  return date ? DAY_TIME.format(date) : iso;
}
