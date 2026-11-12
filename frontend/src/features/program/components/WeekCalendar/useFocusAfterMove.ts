import { useEffect, useRef } from "react";

/**
 * Après un déplacement par le menu, la carte change de colonne (nouveau nœud) et le focus serait
 * perdu : on le rend au bouton « Déplacer » de la carte dès qu'elle s'affiche dans son nouveau jour.
 * `moved(taskId)` se déclare avant d'envoyer le déplacement ; `version` change avec la semaine.
 */
export function useFocusAfterMove(version: unknown) {
  const gridRef = useRef<HTMLDivElement>(null);
  const pending = useRef<string | null>(null);

  useEffect(() => {
    const taskId = pending.current;
    if (taskId === null) return;
    const card = gridRef.current?.querySelector(`[data-task-id="${CSS.escape(taskId)}"]`);
    const trigger = card?.querySelector<HTMLElement>('[aria-haspopup="menu"]');
    if (!trigger) return;
    trigger.focus();
    pending.current = null;
  }, [version]);

  const moved = (taskId: string) => {
    pending.current = taskId;
  };
  return { gridRef, moved };
}
