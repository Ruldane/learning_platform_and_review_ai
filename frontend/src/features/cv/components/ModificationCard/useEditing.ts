import { useState } from "react";
import type { DecideOptions, DecideResult, DecisionView, ModificationView } from "../viewTypes";

/**
 * Is the text the one proposed? Spaces at the edges do not count (the field strips them on send).
 */
export const isUnchanged = (text: string, proposed: string): boolean =>
  text.trim() === proposed.trim();

/**
 * The editor of a modification: it stays open, with the typed text kept, until the back end
 * has decided. A corrected text goes without `confirm` (it was never shown with its blocks, so
 * the back end re-validates it); unchanged text keeps the checkbox confirmation.
 */
export function useEditing(
  mod: ModificationView,
  opts: DecideOptions,
  onDecide: (status: DecisionView, opts?: DecideOptions) => DecideResult,
) {
  const [editing, setEditing] = useState(false);
  const save = async (after: string) => {
    const saved = await onDecide(
      "accepted",
      isUnchanged(after, mod.after) ? { after, ...opts } : { after },
    );
    if (saved !== false) setEditing(false);
  };
  return {
    editing,
    save: (after: string) => void save(after),
    open: () => setEditing(true),
    close: () => setEditing(false),
  };
}
