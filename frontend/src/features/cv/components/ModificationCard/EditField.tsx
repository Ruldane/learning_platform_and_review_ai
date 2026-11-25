import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import { Button } from "@/shared/ui/button";
import { MAX_EDIT_CHARS } from "../viewTypes";
import { isUnchanged } from "./useEditing";

interface EditFieldProps {
  initial: string;
  /** False until a fact to confirm is confirmed: unchanged text cannot be saved. */
  confirmed: boolean;
  busy: boolean;
  onSave: (text: string) => void;
  onCancel: () => void;
}

/** The field that opens with « Modifier »: the proposed text, to correct then accept. */
export function EditField({ initial, confirmed, busy, onSave, onCancel }: EditFieldProps) {
  const id = useId();
  const [text, setText] = useState(initial);
  const empty = text.trim() === "";
  // A corrected text goes without confirmation (the back end re-checks it); only the unchanged
  // text of a modification marked « à confirmer » waits for the checkbox.
  const needsConfirm = !confirmed && isUnchanged(text, initial);
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm font-medium">
        {t("cv.mod.editLabel")}
      </label>
      <textarea
        id={id}
        rows={3}
        maxLength={MAX_EDIT_CHARS}
        value={text}
        disabled={busy}
        onChange={(event) => setText(event.target.value)}
        aria-describedby={`${id}-hint`}
        className={`${fieldClass} h-auto py-1.5`}
      />
      <p id={`${id}-hint`} className="text-xs text-muted-foreground">
        {!needsConfirm ? t("cv.mod.editHint", { max: MAX_EDIT_CHARS }) : t("cv.mod.confirmFirst")}
      </p>
      <div className="flex gap-2">
        <Button onClick={() => onSave(text.trim())} disabled={busy || empty || needsConfirm}>
          {t("cv.mod.editSave")}
        </Button>
        <Button variant="outline" onClick={onCancel} disabled={busy}>
          {t("cv.mod.editCancel")}
        </Button>
      </div>
    </div>
  );
}
