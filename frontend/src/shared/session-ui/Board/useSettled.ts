import { useEffect, useState } from "react";

/**
 * Silence attendu après le dernier signal d'Excalidraw. Excalidraw ajuste la scène juste après
 * l'avoir reçue (flèches liées recalculées, texte mesuré, polices appliquées) et signale ces
 * changements avec un léger retard : on les laisse passer avant d'ouvrir l'édition.
 */
export const QUIET_MS = 250;

/** `true` quand les polices de la page sont chargées (ou quand le navigateur ne sait pas le dire). */
function useFontsReady(): boolean {
  const [ready, setReady] = useState(() => typeof document.fonts === "undefined");
  useEffect(() => {
    if (typeof document.fonts === "undefined") return;
    let alive = true;
    void document.fonts.ready.then(() => {
      if (alive) setReady(true);
    });
    return () => {
      alive = false;
    };
  }, []);
  return ready;
}

/**
 * `true` une fois la scène entière affichée et stabilisée : les polices sont chargées
 * (`document.fonts.ready`) et Excalidraw n'a plus rien signalé pendant `QUIET_MS`. Alors seulement
 * le canevas devient modifiable et ses changements comptent comme ceux de January. Chaque
 * changement avant ce moment (`changeTick` croît à chaque signal) relance l'attente et devient la
 * référence des retouches, jamais une retouche. Même sans animation (état déjà vu, mouvement
 * réduit), le canevas reste en lecture seule le temps de ce calme.
 */
export function useSettled(done: boolean, changeTick: number): boolean {
  const fontsReady = useFontsReady();
  const [settled, setSettled] = useState(false);
  useEffect(() => {
    if (!done || !fontsReady || settled) return;
    const timer = setTimeout(() => setSettled(true), QUIET_MS);
    return () => clearTimeout(timer);
  }, [done, fontsReady, settled, changeTick]);
  return settled;
}
