import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";

interface CapFieldProps {
  label: string;
  value: number;
  min: number;
  max: number;
  onValid: (value: number) => void;
}

function isValid(text: string, min: number, max: number): boolean {
  const n = Number(text);
  return text.trim() !== "" && Number.isInteger(n) && n >= min && n <= max;
}

/**
 * Champ entier borné. La saisie en cours (`draft`) n'existe que pendant l'édition : valide, elle
 * est transmise ; invalide ou vide, elle reste affichée avec un message et rien n'est transmis.
 * En quittant le champ, on revient à la dernière valeur valide.
 */
export function CapField({ label, value, min, max, onValid }: CapFieldProps) {
  const [draft, setDraft] = useState<string | null>(null);
  const inputId = useId();
  const errorId = useId();
  const invalid = draft !== null && !isValid(draft, min, max);

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
