import { useEffect, useRef } from "react";

/**
 * After a move from the menu, the card changes column (new node) and focus would be
 * lost: we return it to the card's « Déplacer » button as soon as it shows on its new day.
 * `moved(taskId)` is declared before sending the move; `version` changes with the week.
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
