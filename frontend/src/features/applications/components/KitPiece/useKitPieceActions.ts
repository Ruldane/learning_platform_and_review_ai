import { useRef, useState, type RefObject } from "react";
import { t } from "@/shared/i18n/t";
import type { KitSaveResult, KitStatusView } from "../viewTypes";

function savedMessage(status: KitStatusView): string {
  if (status === "ready") return t("applications.kitPiece.savedReady");
  if (status === "to_check") return t("applications.kitPiece.savedToCheck");
  return t("applications.kitPiece.saved");
}

interface Draft {
  /** The text to send to the server. */
  text: string;
  /** The server accepted the change. */
  markSaved: () => void;
}

interface Handlers {
  onSave: (content: string) => Promise<KitSaveResult>;
  onCopy: (text: string) => void | Promise<void>;
}

/**
 * What January does with a piece: save it (focus returns to the text being edited,
 * the button is disabled: `root` is the piece) and copy one of its texts. `note` is the last
 * result, read in a live region; `error` is the server's refusal.
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
    /** January edits the text `key`: the note disappears; focus returns to it after saving. */
    edited: (key: string) => {
      lastEdited.current = key;
      setNote("");
    },
  };
}
