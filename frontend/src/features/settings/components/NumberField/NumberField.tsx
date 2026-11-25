import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import { errorHint } from "../errorHint";

interface NumberFieldProps {
  label: string;
  /** Text: the entry may be empty or incomplete without the field rewriting it. */
  value: string;
  min?: number;
  max?: number;
  /** The bounds stated under the field; by default « Entre {min} et {max}. ». */
  hint?: string;
  /** Hors bornes (rouge, `aria-invalid`). */
  invalid: boolean;
  /**
   * Is the field's own help in error? By default: when the field is. False when the
   * field is marked for another reason (the order of two bounds) and its value is
   * within the bounds: the help must not say "Erreur".
   */
  hintError?: boolean;
  /** Refused by the server: the value is never quoted, only the field. */
  refused?: boolean;
  /** Id of one more message describing this field (e.g. the order of the two bounds). */
  describedBy?: string;
  onChange: (value: string) => void;
}

function rangeHint(min?: number, max?: number): string {
  return min !== undefined && max !== undefined ? t("settings.fields.range", { min, max }) : "";
}

/** A whole number with its bounds stated under the field (red when exceeded). */
export function NumberField({
  label,
  value,
  min,
  max,
  hint,
  invalid,
  hintError,
  refused = false,
  describedBy,
  onChange,
}: NumberFieldProps) {
  const hintId = useId();
  const bad = invalid || refused;
  const hintBad = hintError ?? bad;
  const text = errorHint(
    hintBad,
    refused && !invalid ? t("settings.fields.refused") : (hint ?? rangeHint(min, max)),
  );
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium">
        {label}
        <input
          type="number"
          inputMode="numeric"
          min={min}
          max={max}
          step={1}
          value={value}
          aria-invalid={bad}
          aria-describedby={describedBy ? `${hintId} ${describedBy}` : hintId}
          onChange={(event) => onChange(event.target.value)}
          className={`${fieldClass} mt-1 max-w-40`}
        />
      </label>
      <p
        id={hintId}
        className={hintBad ? "text-sm text-destructive" : "text-sm text-muted-foreground"}
      >
        {text}
      </p>
    </div>
  );
}
