import { useEffect, useRef } from "react";

/**
 * Après un déplacement par le menu, la carte change de colonne (nouveau nœud) et le focus serait
 * perdu : on le rend au bouton « Déplacer » de la carte dès qu'elle s'affiche dans sa nouvelle
 * colonne. `moved(id)` se déclare avant d'envoyer le déplacement ; `version` change avec les fiches.
 */
export function useFocusAfterMove(version: unknown) {
  const boardRef = useRef<HTMLDivElement>(null);
  const pending = useRef<string | null>(null);

  useEffect(() => {
    const id = pending.current;
    if (id === null) return;
    const card = boardRef.current?.querySelector(`[data-application-id="${CSS.escape(id)}"]`);
    const trigger = card?.querySelector<HTMLElement>('[aria-haspopup="menu"]');
    if (!trigger) return;
    trigger.focus();
    pending.current = null;
  }, [version]);

  const moved = (id: string) => {
    pending.current = id;
  };
  return { boardRef, moved };
}
