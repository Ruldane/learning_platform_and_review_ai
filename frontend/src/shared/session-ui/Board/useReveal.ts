import { useEffect, useMemo, useState } from "react";
import { revealDelays, revealUnits } from "./reveal";

interface Revealable {
  id: string;
  containerId?: string | null;
}

/**
 * Reveals the elements one by one (200 ms apart, SPEC 3.3). `animate` false or reduced motion:
 * everything is there at once. Renders the elements visible, and `done` when none are missing.
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
