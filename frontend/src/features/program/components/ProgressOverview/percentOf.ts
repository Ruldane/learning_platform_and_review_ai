/** Whole-number share of `done` in `planned`, from 0 to 100 (0 when nothing is planned). */
export function percentOf(done: number, planned: number): number {
  if (planned <= 0) return 0;
  return Math.min(100, Math.max(0, Math.round((done / planned) * 100)));
}
