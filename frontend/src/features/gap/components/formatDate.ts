const SHORT = new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "2-digit" });

/** « 03/11 » : le jour et le mois d'un instant ISO ; une date illisible est rendue telle quelle. */
export function shortDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : SHORT.format(date);
}
