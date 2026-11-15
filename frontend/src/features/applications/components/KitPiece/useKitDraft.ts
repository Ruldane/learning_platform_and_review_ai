import { useMemo, useState } from "react";
import type { KitKindView } from "../viewTypes";
import { joinParts, splitParts, type Part } from "./parts";

/** Ce que le serveur accepte d'une pièce (`KitPatch.content`). */
export const MAX_CONTENT = 20_000;

interface Edit {
  /** Le texte du serveur au moment où January a commencé à modifier. */
  base: string;
  parts: Part[];
  /** Le serveur a pris ce texte : on le montre jusqu'à ce que la lecture du kit le rapporte. */
  saved: boolean;
}

/**
 * Le brouillon d'une pièce : les morceaux du texte du serveur tant que January n'y a rien changé,
 * ses retouches ensuite. Une relecture du kit ne les écrase jamais ; `changedUnder` dit que le
 * texte du serveur a changé entre-temps. Une fois enregistré, le brouillon reste affiché jusqu'à
 * ce que le texte du serveur change : le champ ne repasse pas par l'ancien texte.
 */
export function useKitDraft(kind: KitKindView, content: string) {
  const [edit, setEdit] = useState<Edit | null>(null);
  const stored = useMemo(() => splitParts(kind, content), [kind, content]);
  if (edit?.saved && content !== edit.base) setEdit(null);
  const parts = edit?.parts ?? stored;
  const text = joinParts(kind, parts);
  const dirty = edit !== null && !edit.saved && text !== joinParts(kind, stored);
  return {
    parts,
    dirty,
    changedUnder: dirty && edit.base !== content,
    /** Le texte à envoyer au serveur. */
    text,
    tooLong: text.length > MAX_CONTENT,
    change: (key: string, value: string) =>
      setEdit({
        base: edit && !edit.saved ? edit.base : content,
        parts: parts.map((part) => (part.key === key ? { ...part, text: value } : part)),
        saved: false,
      }),
    /** Le serveur a pris la modification. */
    markSaved: () => setEdit((current) => current && { ...current, saved: true }),
  };
}
