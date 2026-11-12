/** Part entière de `done` dans `planned`, de 0 à 100 (0 quand rien n'est prévu). */
export function percentOf(done: number, planned: number): number {
  if (planned <= 0) return 0;
  return Math.min(100, Math.max(0, Math.round((done / planned) * 100)));
}
