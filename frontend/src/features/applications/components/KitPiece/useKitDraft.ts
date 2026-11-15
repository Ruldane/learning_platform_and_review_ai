import { useMemo, useState } from "react";
import type { KitKindView } from "../viewTypes";
import { joinParts, splitParts, type Part } from "./parts";

interface Edit {
  /** Le texte du serveur au moment où January a commencé à modifier. */
  base: string;
  parts: Part[];
}

/**
 * Le brouillon d'une pièce : les morceaux du texte du serveur tant que January n'y a rien changé,
 * ses retouches ensuite. Une relecture du kit ne les écrase jamais ; `changedUnder` dit que le
 * texte du serveur a changé entre-temps.
 */
export function useKitDraft(kind: KitKindView, content: string) {
  const [edit, setEdit] = useState<Edit | null>(null);
  const stored = useMemo(() => splitParts(kind, content), [kind, content]);
  const parts = edit?.parts ?? stored;
  const dirty = edit !== null && joinParts(kind, edit.parts) !== joinParts(kind, stored);
  return {
    parts,
    dirty,
    changedUnder: dirty && edit.base !== content,
    /** Le texte à envoyer au serveur. */
    text: () => joinParts(kind, parts),
    change: (key: string, text: string) =>
      setEdit({
        base: edit?.base ?? content,
        parts: parts.map((part) => (part.key === key ? { ...part, text } : part)),
      }),
    /** Le serveur a pris la modification : on repart de son texte. */
    clear: () => setEdit(null),
  };
}
