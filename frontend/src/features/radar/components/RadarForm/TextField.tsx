import { useId } from "react";
import { fieldClass } from "@/shared/ui/fieldClass";

interface TextFieldProps {
  label: string;
  value: string;
  /** A sweep is running: the field stays readable and keeps focus (`readOnly`, not `disabled`). */
  disabled: boolean;
  /** The field's error message; `undefined` when it is valid. */
  error?: string;
  onChange: (value: string) => void;
}

/** A text field for launching a sweep: label, input of 120 characters at most, and error. */
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
        readOnly={disabled}
        aria-disabled={disabled}
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
