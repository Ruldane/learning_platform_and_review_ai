import { useId } from "react";
import { fieldClass } from "@/shared/ui/fieldClass";
import { FieldMessages } from "./FieldMessages";

interface EntryFieldProps {
  label: string;
  value: string;
  disabled: boolean;
  error: string | undefined;
  hint?: string;
  /** Several lines: a `textarea` of this height; without it, a single-line field. */
  rows?: number;
  onChange: (value: string) => void;
}

/** A field of the profile entry form: label, optional hint and error message. */
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
