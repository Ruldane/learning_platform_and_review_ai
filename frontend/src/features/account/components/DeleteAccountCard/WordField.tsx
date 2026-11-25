import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";

interface WordFieldProps {
  value: string;
  /** A refusal targets this field: `aria-invalid`. */
  invalid: boolean;
  /** The texts describing the field: the warnings, then the failure if there is one. */
  describedBy: string;
  onChange: (value: string) => void;
}

/** The field where the confirmation word is retyped: no autocomplete, no autocorrect, no
 * capitals. */
export function WordField({ value, invalid, describedBy, onChange }: WordFieldProps) {
  const inputId = useId();
  return (
    <>
      <label htmlFor={inputId} className="text-sm font-medium">
        {t("account.delete.label")}
      </label>
      <input
        id={inputId}
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete="off"
        autoCapitalize="off"
        spellCheck={false}
        aria-invalid={invalid ? true : undefined}
        aria-describedby={describedBy}
        className={`${fieldClass} max-w-xs`}
      />
    </>
  );
}
