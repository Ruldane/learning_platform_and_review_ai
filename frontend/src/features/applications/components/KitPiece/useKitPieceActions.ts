import { useRef, useState, type RefObject } from "react";
import { t } from "@/shared/i18n/t";
import type { KitSaveResult, KitStatusView } from "../viewTypes";

function savedMessage(status: KitStatusView): string {
  if (status === "ready") return t("applications.kitPiece.savedReady");
  if (status === "to_check") return t("applications.kitPiece.savedToCheck");
  return t("applications.kitPiece.saved");
}

interface Draft {
  /** Le texte à envoyer au serveur. */
  text: string;
  /** Le serveur a pris la modification. */
  markSaved: () => void;
}

interface Handlers {
  onSave: (content: string) => Promise<KitSaveResult>;
  onCopy: (text: string) => void | Promise<void>;
}

/**
 * Ce que January fait d'une pièce : l'enregistrer (le focus revient au texte qu'elle modifiait,
 * le bouton se désactive : `root` est la pièce) et copier un de ses textes. `note` est le dernier
 * résultat, lu dans une zone vocale ; `error` le refus du serveur.
 */
export function useKitPieceActions(
  root: RefObject<HTMLElement | null>,
  draft: Draft,
  { onSave, onCopy }: Handlers,
) {
  const [saving, setSaving] = useState(false);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const lastEdited = useRef<string | null>(null);

  function refocus() {
    const field = lastEdited.current
      ? root.current?.querySelector<HTMLElement>(`[data-part="${lastEdited.current}"]`)
      : null;
    (field ?? root.current?.querySelector<HTMLElement>("textarea"))?.focus();
  }

  async function save() {
    setSaving(true);
    setError("");
    const result = await onSave(draft.text);
    setSaving(false);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    draft.markSaved();
    setNote(savedMessage(result.status));
    refocus();
  }

  async function copy(content: string) {
    try {
      await onCopy(content);
      setNote(t("applications.kitPiece.copied"));
    } catch {
      setNote(t("applications.kitPiece.copyFailed"));
    }
  }

  return {
    saving,
    note,
    error,
    save,
    copy,
    /** January modifie le texte `key` : la note disparaît, le focus lui reviendra après l'enregistrement. */
    edited: (key: string) => {
      lastEdited.current = key;
      setNote("");
    },
  };
}
