import { useId, type ReactNode } from "react";

/** Ce que le champ natif reçoit pour être relié à son étiquette, à son aide et à son erreur. */
export interface FieldControlProps {
  id: string;
  "aria-describedby": string | undefined;
  "aria-invalid": true | undefined;
}

interface FieldProps {
  label: string;
  hint?: string;
  /** Une erreur : lue avec le champ (`aria-describedby`) et annoncée. */
  error?: string;
  children: (control: FieldControlProps) => ReactNode;
}

/** Une étiquette reliée à son champ, avec une aide facultative et une erreur facultative. */
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
