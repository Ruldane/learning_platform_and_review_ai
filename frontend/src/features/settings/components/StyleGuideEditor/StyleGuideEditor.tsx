import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import { errorHint } from "../errorHint";

interface StyleGuideEditorProps {
  value: string;
  /** Refused by the server: the text is never quoted, only the field. */
  refused?: boolean;
  onChange: (value: string) => void;
}

/** The personal style guide: free text and the character count. */
export function StyleGuideEditor({ value, refused = false, onChange }: StyleGuideEditorProps) {
  const id = useId();
  const hintId = useId();
  const count = [...value].length;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {t("settings.style.label")}
      </label>
      <textarea
        id={id}
        value={value}
        rows={12}
        aria-invalid={refused}
        aria-describedby={hintId}
        onChange={(event) => onChange(event.target.value)}
        className={`${fieldClass} h-auto min-h-48 py-2 leading-relaxed`}
      />
      <p id={hintId} className="flex flex-wrap justify-between gap-2 text-sm text-muted-foreground">
        <span className={refused ? "text-destructive" : undefined}>
          {errorHint(refused, refused ? t("settings.fields.refused") : t("settings.style.hint"))}
        </span>
        <span>
          {t(count === 1 ? "settings.style.countOne" : "settings.style.count", {
            count: count.toLocaleString("en-GB"),
          })}
        </span>
      </p>
    </div>
  );
}
