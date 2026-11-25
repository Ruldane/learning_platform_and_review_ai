import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import { MAX_NOTE_CHARS } from "../viewTypes";

interface NoteFieldProps {
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
}

/** The optional note: what the documents do not say, 4,000 characters at most. */
export function NoteField({ value, disabled, onChange }: NoteFieldProps) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {t("cv.import.noteLabel")}
      </label>
      <textarea
        id={id}
        rows={4}
        maxLength={MAX_NOTE_CHARS}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        aria-describedby={`${id}-hint`}
        className={`${fieldClass} h-auto py-1.5`}
      />
      <p id={`${id}-hint`} className="text-xs text-muted-foreground">
        {t("cv.import.noteHint")}
      </p>
    </div>
  );
}
