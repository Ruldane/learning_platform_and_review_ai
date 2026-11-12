const POINTS = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });

/** « 1 », « 0,5 », « 7,5 » : les points se comptent par demi. */
export function formatPoints(points: number): string {
  return POINTS.format(points);
}
