import { useContext, useId } from "react";
import { fieldClass } from "@/shared/ui/fieldClass";
import { FieldErrorsContext } from "./fieldErrors";

interface FieldProps {
  /** Path of the field in the profile (`experiences.0.role`): it is what maps the 422 error. */
  path: string;
  label: string;
  /** The row it belongs to (« Expérience 2 »): added to the field's accessible name. */
  context?: string;
  value: string;
  onChange: (value: string) => void;
  multiline?: boolean;
  maxLength?: number;
  required?: boolean;
}

/** A profile field: label, input, and below it the server error that points to it. */
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
