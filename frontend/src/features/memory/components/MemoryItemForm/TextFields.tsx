import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { Draft } from "./itemFormModel";

interface TextFieldsProps {
  draft: Draft;
  disabled: boolean;
  onChange: (patch: Partial<Draft>) => void;
}

const labelClass = "flex flex-col gap-1 text-sm font-medium";

/** Titre, texte et étiquettes (séparées par des virgules). */
export function TextFields({ draft, disabled, onChange }: TextFieldsProps) {
  const tagsId = useId();
  const hintId = useId();
  return (
    <>
      <label className={labelClass}>
        {t("memory.form.title")}
        <input
          type="text"
          value={draft.title}
          disabled={disabled}
          maxLength={200}
          onChange={(e) => onChange({ title: e.target.value })}
          className={fieldClass}
        />
      </label>
      <label className={labelClass}>
        {t("memory.form.text")}
        <textarea
          value={draft.text}
          disabled={disabled}
          rows={8}
          onChange={(e) => onChange({ text: e.target.value })}
          className={`${fieldClass} h-auto py-1.5`}
        />
      </label>
      <div className="flex flex-col gap-1">
        <label htmlFor={tagsId} className="text-sm font-medium">
          {t("memory.form.tags")}
        </label>
        <input
          id={tagsId}
          type="text"
          value={draft.tags}
          disabled={disabled}
          aria-describedby={hintId}
          onChange={(e) => onChange({ tags: e.target.value })}
          className={fieldClass}
        />
        <span id={hintId} className="text-xs text-muted-foreground">
          {t("memory.form.tagsHint")}
        </span>
      </div>
    </>
  );
}
