import { useState } from "react";
import type { DecideOptions, DecideResult, DecisionView, ModificationView } from "../viewTypes";

/** Le texte est-il celui proposé ? Les espaces en bord ne comptent pas (le champ les retire à l'envoi). */
export const isUnchanged = (text: string, proposed: string): boolean =>
  text.trim() === proposed.trim();

/**
 * L'éditeur d'une modification : il reste ouvert, texte saisi gardé, tant que le back n'a pas pris
 * la décision. Un texte corrigé repart sans `confirm` (il n'a jamais été montré avec ses blocs, le
 * back le revalide) ; le texte inchangé garde la confirmation de la case.
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
