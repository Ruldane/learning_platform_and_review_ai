import { useEffect, useState } from "react";

/**
 * Excalidraw ajuste la scène juste après l'avoir reçue (flèches liées recalculées, texte mesuré)
 * et signale ces changements avec un léger retard : on les laisse passer avant d'ouvrir l'édition.
 */
export const SETTLE_MS = 250;

/**
 * `true` une fois la scène entière affichée et stabilisée : alors seulement le canevas devient
 * modifiable et ses changements comptent comme ceux de January. Même sans animation (état déjà vu,
 * mouvement réduit), le canevas reste `SETTLE_MS` en lecture seule : les ajustements d'Excalidraw
 * deviennent la référence des retouches, jamais une retouche.
 */
export function useSettled(done: boolean): boolean {
  const [settled, setSettled] = useState(false);
  useEffect(() => {
    if (!done) return;
    const timer = setTimeout(() => setSettled(true), SETTLE_MS);
    return () => clearTimeout(timer);
  }, [done]);
  return settled;
}
