import { useEffect, useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";

interface CapFieldProps {
  label: string;
  value: number;
  min: number;
  max: number;
  onValid: (value: number) => void;
  /** Tells the parent that the current entry is invalid (it must then refuse sending). */
  onInvalidChange?: (invalid: boolean) => void;
}

function isValid(text: string, min: number, max: number): boolean {
  const n = Number(text);
  return text.trim() !== "" && Number.isInteger(n) && n >= min && n <= max;
}

/**
 * Bounded whole-number field. The current entry (`draft`) exists only while editing: when valid,
 * it is passed on; when invalid or empty, it stays shown with a message and nothing is passed on.
 * On leaving the field, it goes back to the last valid value.
 */
export function CapField({ label, value, min, max, onValid, onInvalidChange }: CapFieldProps) {
  const [draft, setDraft] = useState<string | null>(null);
  const inputId = useId();
  const errorId = useId();
  const invalid = draft !== null && !isValid(draft, min, max);

  useEffect(() => {
    onInvalidChange?.(invalid);
    return () => onInvalidChange?.(false);
  }, [invalid, onInvalidChange]);

  function onChange(next: string) {
    setDraft(next);
    if (isValid(next, min, max)) onValid(Number(next));
  }

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={inputId} className="text-sm font-medium">
        {label}
      </label>
      <input
        id={inputId}
        type="number"
        inputMode="numeric"
        min={min}
        max={max}
        step={1}
        value={draft ?? String(value)}
        aria-invalid={invalid}
        aria-describedby={invalid ? errorId : undefined}
        onChange={(event) => onChange(event.target.value)}
        onBlur={() => setDraft(null)}
        className={fieldClass}
      />
      {invalid && (
        <p id={errorId} role="alert" className="text-sm text-destructive">
          {t("settings.search.caps.range", { min, max })}
        </p>
      )}
    </div>
  );
}
