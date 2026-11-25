import { useMemo, useState } from "react";
import type { KitKindView } from "../viewTypes";
import { joinParts, MAX_CONTENT, splitParts, type Part } from "./parts";

interface Edit {
  /** The server's text when January started editing. */
  base: string;
  parts: Part[];
  /** The server took this text: it is shown until the kit read reports it. */
  saved: boolean;
}

/**
 * A piece's draft: the parts of the server's text while January has changed nothing,
 * its edits after that. A kit re-read never overwrites them; `changedUnder` says that the
 * server's text changed in the meantime. Once saved, the draft stays shown until
 * the server's text changes: the field does not go back through the old text.
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
    /** The text to send to the server. */
    text,
    tooLong: text.length > MAX_CONTENT,
    change: (key: string, value: string) =>
      setEdit({
        base: edit && !edit.saved ? edit.base : content,
        parts: parts.map((part) => (part.key === key ? { ...part, text: value } : part)),
        saved: false,
      }),
    /** The server accepted the change. */
    markSaved: () => setEdit((current) => current && { ...current, saved: true }),
  };
}
