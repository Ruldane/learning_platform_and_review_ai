import { useState } from "react";
import type { ProposalView } from "../viewTypes";

/**
 * Cards checked for the mix, in card order. A checked card that is no longer proposed
 * (another batch of proposals) is forgotten; the limit of two is enforced by the UI (checkbox
 * disabled), not here.
 */
export function useMixSelection(ordered: ProposalView[]) {
  const [ticked, setTicked] = useState<string[]>([]);
  const picked = ordered.filter((p) => ticked.includes(p.id)).map((p) => p.id);
  const toggle = (id: string) =>
    setTicked(picked.includes(id) ? picked.filter((p) => p !== id) : [...picked, id]);
  return { picked, toggle };
}
