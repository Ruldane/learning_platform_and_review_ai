import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { PostingTab } from "./PostingTabs";

interface SourcePanelProps {
  kind: PostingTab;
  id: string;
  hidden: boolean;
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
}

/** A tab's panel: the link field (one line) or the pasted text (a textarea), with its help. */
export function SourcePanel({ kind, id, hidden, value, disabled, onChange }: SourcePanelProps) {
  const field = {
    id,
    value,
    disabled,
    "aria-describedby": `${id}-hint`,
    onChange: (event: { target: { value: string } }) => onChange(event.target.value),
  };
  return (
    <div
      role="tabpanel"
      id={`${id}-panel`}
      aria-labelledby={`${id}-tab`}
      hidden={hidden}
      className="flex flex-col gap-1"
    >
      <label htmlFor={id} className="text-sm font-medium">
        {t(kind === "url" ? "gap.form.urlLabel" : "gap.form.textLabel")}
      </label>
      {kind === "url" ? (
        <input
          {...field}
          type="text"
          inputMode="url"
          autoComplete="off"
          maxLength={2048}
          className={fieldClass}
        />
      ) : (
        <textarea {...field} rows={8} maxLength={60000} className={`${fieldClass} h-auto py-1.5`} />
      )}
      <p id={`${id}-hint`} className="text-xs text-muted-foreground">
        {t(kind === "url" ? "gap.form.urlHint" : "gap.form.textHint")}
      </p>
    </div>
  );
}
