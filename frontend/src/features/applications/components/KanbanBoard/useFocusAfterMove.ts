import { useEffect, useRef } from "react";
import type { StatusView } from "../viewTypes";

/** Ce qui reprend le focus : le bouton « Déplacer » (menu) ou la poignée de glisser (clavier). */
export type FocusTarget = "menu" | "handle";

const SELECTOR: Record<FocusTarget, string> = {
  menu: '[aria-haspopup="menu"]',
  handle: "[data-drag-handle]",
};

interface Pending {
  id: string;
  status: StatusView;
  target: FocusTarget;
}

/**
 * Après un déplacement, la carte change de colonne (nouveau nœud) et le focus serait perdu : on le
 * rend à la poignée ou au bouton « Déplacer » dès que la carte s'affiche dans sa nouvelle colonne.
 * `moved` se déclare avant d'envoyer le déplacement ; `version` change avec les fiches. Si la carte
 * est relue dans une autre colonne (déplacement refusé, ou rafraîchissement sans rapport), l'attente
 * s'arrête : un rafraîchissement ultérieur ne vole jamais le focus.
 */
export function useFocusAfterMove(version: unknown) {
  const boardRef = useRef<HTMLDivElement>(null);
  const pending = useRef<Pending | null>(null);

  useEffect(() => {
    const wanted = pending.current;
    if (wanted === null) return;
    const card = boardRef.current?.querySelector(
      `[data-application-id="${CSS.escape(wanted.id)}"]`,
    );
    if (!card) return;
    pending.current = null;
    const column = card.closest<HTMLElement>("[data-status]");
    if (column?.dataset.status !== wanted.status) return;
    card.querySelector<HTMLElement>(SELECTOR[wanted.target])?.focus();
  }, [version]);

  const moved = (id: string, status: StatusView, target: FocusTarget) => {
    pending.current = { id, status, target };
  };
  return { boardRef, moved };
}
