/** Pause between two board elements the Scribe fills in (SPEC 3.3: 150 to 300 ms). */
export const REVEAL_STEP_MS = 200;
const MIN_STEP_MS = 150;
const MAX_STEP_MS = 300;

/**
 * Cumulative delays (ms) for `count` elements to appear: the first at once, then a step
 * bounded to [150, 300]. Reduced motion: everything appears at once.
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
 * Groups of elements that appear together, in the converter's order (Mermaid write order):
 * a label attached to a shape appears with it, not after.
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
