import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { InterruptField } from "./fieldAnswers";

interface Props {
  id: string;
  field: InterruptField;
  value: string;
  disabled: boolean;
  focus: boolean;
  onChange: (value: string) => void;
}

export function InterruptTextField({ id, field, value, disabled, focus, onChange }: Props) {
  const requiredHint = `${id}-req`;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {field.label}
      </label>
      <textarea
        id={id}
        rows={2}
        value={value}
        maxLength={field.max_length}
        required={field.required}
        disabled={disabled}
        autoFocus={focus}
        aria-describedby={field.required ? requiredHint : undefined}
        onChange={(event) => onChange(event.target.value)}
        className={cn(fieldClass, "h-auto min-h-16 py-1.5")}
      />
      {field.required && (
        <span id={requiredHint} className="text-xs text-muted-foreground">
          {t("session.interrupt.required")}
        </span>
      )}
    </div>
  );
}
