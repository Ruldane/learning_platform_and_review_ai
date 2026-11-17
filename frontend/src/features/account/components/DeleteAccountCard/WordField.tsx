import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";

interface WordFieldProps {
  value: string;
  /** Le refus vise ce champ : `aria-invalid`. */
  invalid: boolean;
  /** Les textes qui décrivent le champ : les avertissements, puis l'échec s'il y en a un. */
  describedBy: string;
  onChange: (value: string) => void;
}

/** Le champ où l'on retape le mot de confirmation : ni complétion, ni correction, ni majuscule. */
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
