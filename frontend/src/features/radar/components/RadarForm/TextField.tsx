import { useId } from "react";
import { fieldClass } from "@/shared/ui/fieldClass";

interface TextFieldProps {
  label: string;
  value: string;
  disabled: boolean;
  /** Le message d'erreur du champ ; `undefined` quand il est correct. */
  error?: string;
  onChange: (value: string) => void;
}

/** Un champ texte du lancement d'un relevé : libellé, saisie de 120 caractères au plus et erreur. */
export function TextField({ label, value, disabled, error, onChange }: TextFieldProps) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <input
        id={id}
        value={value}
        maxLength={120}
        disabled={disabled}
        aria-invalid={error !== undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        onChange={(event) => onChange(event.target.value)}
        className={fieldClass}
      />
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}
