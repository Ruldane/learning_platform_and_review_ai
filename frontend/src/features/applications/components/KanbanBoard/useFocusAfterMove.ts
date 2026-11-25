import { useEffect, useRef } from "react";
import type { StatusView } from "../viewTypes";

/** What takes focus back: the « Déplacer » button (menu) or the drag handle (keyboard). */
export type FocusTarget = "menu" | "handle";

const SELECTOR: Record<FocusTarget, string> = {
  menu: '[aria-haspopup="menu"]',
  handle: "[data-drag-handle]",
};

interface Move {
  id: string;
  /** The column the card leaves. */
  from: StatusView;
  /** The column it goes to. */
  to: StatusView;
  target: FocusTarget;
}

function focusCard(root: HTMLElement | null, id: string, target: FocusTarget): void {
  const card = root?.querySelector(`[data-application-id="${CSS.escape(id)}"]`);
  card?.querySelector<HTMLElement>(SELECTOR[target])?.focus();
}

function columnOf(root: HTMLElement | null, id: string): string | null {
  const card = root?.querySelector(`[data-application-id="${CSS.escape(id)}"]`);
  return card?.closest<HTMLElement>("[data-status]")?.dataset.status ?? null;
}

/**
 * After a move, the card changes column (new node) and focus would be lost: it is
 * returned to the handle or « Déplacer » button as soon as the card shows in its new column.
 * `moved` is set before the move is sent; `version` changes with the records.
 *
 * If the card is re-read in another column than expected (move refused, or an unrelated refresh
 * ), the wait stops: a later refresh never steals focus. If the
 * server refuses after the page update, the card goes back to its original column (another
 * node): focus, which fell to the page, is given back once, without taking what it would have
 * already received.
 */
export function useFocusAfterMove(version: unknown) {
  const boardRef = useRef<HTMLDivElement>(null);
  const pending = useRef<Move | null>(null);
  const placed = useRef<Move | null>(null);

  useEffect(() => {
    const root = boardRef.current;
    const wanted = pending.current;
    if (wanted !== null) {
      const column = columnOf(root, wanted.id);
      if (column === null) return;
      pending.current = null;
      if (column !== wanted.to) return;
      focusCard(root, wanted.id, wanted.target);
      placed.current = wanted;
      return;
    }
    const done = placed.current;
    if (done === null) return;
    const column = columnOf(root, done.id);
    if (column === null || column === done.to) return;
    placed.current = null;
    if (column === done.from && document.activeElement === document.body) {
      focusCard(root, done.id, done.target);
    }
  }, [version]);

  const moved = (id: string, from: StatusView, to: StatusView, target: FocusTarget) => {
    placed.current = null;
    pending.current = { id, from, to, target };
  };
  return { boardRef, moved };
}
