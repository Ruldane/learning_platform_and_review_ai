import { useEffect, useState } from "react";

/** Excalidraw signale ses changements avec un léger retard : on laisse la dernière image passer. */
export const SETTLE_MS = 250;

/**
 * `true` une fois la scène entière affichée et stabilisée : alors seulement le canevas devient
 * modifiable et ses changements comptent comme ceux de January. Sans animation : tout de suite.
 */
export function useSettled(done: boolean, instant: boolean): boolean {
  const [settled, setSettled] = useState(instant);
  useEffect(() => {
    if (instant || !done) return;
    const timer = setTimeout(() => setSettled(true), SETTLE_MS);
    return () => clearTimeout(timer);
  }, [done, instant]);
  return instant || settled;
}
