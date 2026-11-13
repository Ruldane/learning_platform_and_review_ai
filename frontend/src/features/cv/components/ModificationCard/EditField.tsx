import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import { Button } from "@/shared/ui/button";
import { MAX_EDIT_CHARS } from "../viewTypes";

interface EditFieldProps {
  initial: string;
  /** Faux tant qu'un fait à confirmer n'est pas confirmé : l'enregistrement est refusé. */
  confirmed: boolean;
  busy: boolean;
  onSave: (text: string) => void;
  onCancel: () => void;
}

/** Le champ qui s'ouvre avec « Modifier » : le texte proposé, à corriger puis à accepter. */
export function EditField({ initial, confirmed, busy, onSave, onCancel }: EditFieldProps) {
  const id = useId();
  const [text, setText] = useState(initial);
  const empty = text.trim() === "";
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
        {confirmed ? t("cv.mod.editHint", { max: MAX_EDIT_CHARS }) : t("cv.mod.confirmFirst")}
      </p>
      <div className="flex gap-2">
        <Button onClick={() => onSave(text.trim())} disabled={busy || empty || !confirmed}>
          {t("cv.mod.editSave")}
        </Button>
        <Button variant="outline" onClick={onCancel} disabled={busy}>
          {t("cv.mod.editCancel")}
        </Button>
      </div>
    </div>
  );
}
