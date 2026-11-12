import { useEffect, useMemo, useState } from "react";
import { revealDelays, revealUnits } from "./reveal";

interface Revealable {
  id: string;
  containerId?: string | null;
}

/**
 * Fait apparaître les éléments un par un (200 ms entre deux, SPEC 3.3). `animate` faux ou mouvement
 * réduit : tout est là tout de suite. Rend les éléments visibles et `done` quand il n'en manque plus.
 */
export function useReveal<T extends Revealable>(
  elements: readonly T[],
  opts: { animate: boolean; reducedMotion: boolean },
): { visible: T[]; done: boolean } {
  const units = useMemo(() => revealUnits(elements), [elements]);
  const instant = !opts.animate || opts.reducedMotion;
  const [count, setCount] = useState(instant ? units.length : 0);

  useEffect(() => {
    if (instant) return;
    const delays = revealDelays(units.length, { reducedMotion: false });
    const timers = delays.map((delay, index) => setTimeout(() => setCount(index + 1), delay));
    return () => timers.forEach(clearTimeout);
  }, [instant, units]);

  const shown = instant ? units.length : Math.min(count, units.length);
  const visible = useMemo(() => units.slice(0, shown).flat(), [units, shown]);
  return { visible, done: shown >= units.length };
}
