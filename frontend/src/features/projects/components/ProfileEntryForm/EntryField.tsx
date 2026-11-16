import { useId } from "react";
import { fieldClass } from "@/shared/ui/fieldClass";
import { FieldMessages } from "./FieldMessages";

interface EntryFieldProps {
  label: string;
  value: string;
  disabled: boolean;
  error: string | undefined;
  hint?: string;
  /** Plusieurs lignes : un `textarea` de cette hauteur ; sans, un champ d'une ligne. */
  rows?: number;
  onChange: (value: string) => void;
}

/** Un champ du formulaire d'entrée de profil : libellé, indication facultative et message d'erreur. */
export function EntryField({
  label,
  value,
  disabled,
  error,
  hint,
  rows,
  onChange,
}: EntryFieldProps) {
  const id = useId();
  const describedBy = [hint ? `${id}-hint` : null, error ? `${id}-error` : null]
    .filter(Boolean)
    .join(" ");
  const common = {
    id,
    value,
    disabled,
    "aria-invalid": error !== undefined,
    "aria-describedby": describedBy || undefined,
  };
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      {rows ? (
        <textarea
          {...common}
          rows={rows}
          onChange={(event) => onChange(event.target.value)}
          className={`${fieldClass} h-auto py-2`}
        />
      ) : (
        <input
          {...common}
          type="text"
          onChange={(event) => onChange(event.target.value)}
          className={fieldClass}
        />
      )}
      <FieldMessages id={id} hint={hint} error={error} />
    </div>
  );
}
