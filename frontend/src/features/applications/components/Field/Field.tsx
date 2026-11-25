import { useId, type ReactNode } from "react";

/** What the native field receives to be linked to its label, its help and its error. */
export interface FieldControlProps {
  id: string;
  "aria-describedby": string | undefined;
  "aria-invalid": true | undefined;
}

interface FieldProps {
  label: string;
  hint?: string;
  /** An error: read with the field (`aria-describedby`) and announced. */
  error?: string;
  children: (control: FieldControlProps) => ReactNode;
}

/** A label linked to its field, with optional help and an optional error. */
export function Field({ label, hint, error, children }: FieldProps) {
  const id = useId();
  const described = [hint ? `${id}-hint` : null, error ? `${id}-error` : null].filter(Boolean);
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      {children({
        id,
        "aria-describedby": described.length > 0 ? described.join(" ") : undefined,
        "aria-invalid": error ? true : undefined,
      })}
      {hint ? (
        <span id={`${id}-hint`} className="text-xs text-muted-foreground">
          {hint}
        </span>
      ) : null}
      {error ? (
        <span id={`${id}-error`} role="alert" className="text-xs text-destructive">
          {error}
        </span>
      ) : null}
    </div>
  );
}
