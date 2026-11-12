/** Pause entre deux éléments du tableau que le Scribe remplit (SPEC 3.3 : 150 à 300 ms). */
export const REVEAL_STEP_MS = 200;
const MIN_STEP_MS = 150;
const MAX_STEP_MS = 300;

/**
 * Délais cumulés (ms) d'apparition de `count` éléments : le premier tout de suite, puis un pas
 * borné à [150, 300]. Mouvement réduit : tout apparaît d'un coup.
 */
export function revealDelays(
  count: number,
  opts: { stepMs?: number; reducedMotion: boolean },
): number[] {
  if (opts.reducedMotion) return Array.from({ length: count }, () => 0);
  const step = Math.min(MAX_STEP_MS, Math.max(MIN_STEP_MS, opts.stepMs ?? REVEAL_STEP_MS));
  return Array.from({ length: count }, (_, index) => index * step);
}

interface Revealable {
  id: string;
  containerId?: string | null;
}

/**
 * Groupes d'éléments qui apparaissent ensemble, dans l'ordre du convertisseur (ordre d'écriture
 * du Mermaid) : une étiquette liée à une forme apparaît avec elle, pas après.
 */
export function revealUnits<T extends Revealable>(elements: readonly T[]): T[][] {
  const unitOf = new Map<string, T[]>();
  const units: T[][] = [];
  for (const element of elements) {
    const host = element.containerId ? unitOf.get(element.containerId) : undefined;
    if (host) {
      host.push(element);
      unitOf.set(element.id, host);
      continue;
    }
    const unit = [element];
    units.push(unit);
    unitOf.set(element.id, unit);
  }
  return units;
}
