import { useState } from "react";
import type { ProposalView } from "../viewTypes";

/**
 * Cartes cochées pour le mélange, dans l'ordre des cartes. Une carte cochée qui n'est plus proposée
 * (autre lot de propositions) est oubliée ; la limite de deux est tenue par l'interface (case
 * désactivée), pas ici.
 */
export function useMixSelection(ordered: ProposalView[]) {
  const [ticked, setTicked] = useState<string[]>([]);
  const picked = ordered.filter((p) => ticked.includes(p.id)).map((p) => p.id);
  const toggle = (id: string) =>
    setTicked(picked.includes(id) ? picked.filter((p) => p !== id) : [...picked, id]);
  return { picked, toggle };
}
