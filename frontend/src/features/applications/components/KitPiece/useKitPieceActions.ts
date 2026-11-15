import { useState, type RefObject } from "react";
import { t } from "@/shared/i18n/t";
import type { KitSaveResult, KitStatusView } from "../viewTypes";

function savedMessage(status: KitStatusView): string {
  if (status === "ready") return t("applications.kitPiece.savedReady");
  if (status === "to_check") return t("applications.kitPiece.savedToCheck");
  return t("applications.kitPiece.saved");
}

interface Handlers {
  /** Le texte à envoyer au serveur. */
  text: () => string;
  /** Le serveur a pris la modification. */
  onSaved: () => void;
  onSave: (content: string) => Promise<KitSaveResult>;
  onCopy: (text: string) => void | Promise<void>;
}

/**
 * Ce que January fait d'une pièce : l'enregistrer (le focus reste dans son texte, le bouton se
 * désactive : `root` est la pièce) et copier un de ses textes. `note` est le dernier résultat, lu dans une zone vocale ;
 * `error` le refus du serveur.
 */
export function useKitPieceActions(
  root: RefObject<HTMLElement | null>,
  { text, onSaved, onSave, onCopy }: Handlers,
) {
  const [saving, setSaving] = useState(false);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");

  async function save() {
    setSaving(true);
    setError("");
    const result = await onSave(text());
    setSaving(false);
    if (!result.ok) {
      setError(result.message);
      return;
    }
    onSaved();
    setNote(savedMessage(result.status));
    root.current?.querySelector("textarea")?.focus();
  }

  async function copy(content: string) {
    try {
      await onCopy(content);
      setNote(t("applications.kitPiece.copied"));
    } catch {
      setNote(t("applications.kitPiece.copyFailed"));
    }
  }

  return { saving, note, error, save, copy, clearNote: () => setNote("") };
}
