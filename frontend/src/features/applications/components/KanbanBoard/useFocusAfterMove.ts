import { useEffect, useRef } from "react";
import type { StatusView } from "../viewTypes";

/** Ce qui reprend le focus : le bouton « Déplacer » (menu) ou la poignée de glisser (clavier). */
export type FocusTarget = "menu" | "handle";

const SELECTOR: Record<FocusTarget, string> = {
  menu: '[aria-haspopup="menu"]',
  handle: "[data-drag-handle]",
};

interface Move {
  id: string;
  /** La colonne d'où la carte part. */
  from: StatusView;
  /** La colonne où elle va. */
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
 * Après un déplacement, la carte change de colonne (nouveau nœud) et le focus serait perdu : on le
 * rend à la poignée ou au bouton « Déplacer » dès que la carte s'affiche dans sa nouvelle colonne.
 * `moved` se déclare avant d'envoyer le déplacement ; `version` change avec les fiches.
 *
 * Si la carte est relue dans une autre colonne que prévu (déplacement refusé, ou rafraîchissement
 * sans rapport), l'attente s'arrête : un rafraîchissement ultérieur ne vole jamais le focus. Si le
 * serveur refuse après la mise à jour de la page, la carte revient dans sa colonne d'origine (autre
 * nœud) : le focus, tombé sur la page, lui est rendu une fois, sans rien prendre à ce qui l'aurait
 * déjà reçu.
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
