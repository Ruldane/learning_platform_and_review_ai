const POINTS = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 1 });

/** « 1 », « 0,5 », « 7,5 »: points are counted in halves. */
export function formatPoints(points: number): string {
  return POINTS.format(points);
}
