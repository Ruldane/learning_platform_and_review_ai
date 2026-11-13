import { useContext, useId } from "react";
import { fieldClass } from "@/shared/ui/fieldClass";
import { FieldErrorsContext } from "./fieldErrors";

interface FieldProps {
  /** Chemin du champ dans le profil (`experiences.0.role`) : c'est lui qui désigne l'erreur 422. */
  path: string;
  label: string;
  /** La ligne dont il fait partie (« Expérience 2 ») : ajoutée au nom accessible du champ. */
  context?: string;
  value: string;
  onChange: (value: string) => void;
  multiline?: boolean;
  maxLength?: number;
  required?: boolean;
}

/** Un champ du profil : libellé, saisie, et sous elle l'erreur du serveur qui le désigne. */
export function Field(props: FieldProps) {
  const { path, label, context, value, onChange, multiline, maxLength, required } = props;
  const id = useId();
  const error = useContext(FieldErrorsContext)[path];
  const shared = {
    id,
    value,
    maxLength,
    "aria-label": context ? `${label} (${context})` : label,
    "aria-required": required || undefined,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": error ? `${id}-error` : undefined,
    onChange: (event: { target: { value: string } }) => onChange(event.target.value),
  };
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      {multiline ? (
        <textarea {...shared} rows={3} className={`${fieldClass} h-auto py-1.5`} />
      ) : (
        <input {...shared} type="text" autoComplete="off" className={fieldClass} />
      )}
      {error ? (
        <p id={`${id}-error`} className="text-xs text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}
