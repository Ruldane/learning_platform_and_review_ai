import { useId } from "react";
import type { ReactNode } from "react";

interface ControlProps {
  id: string;
  "aria-invalid": boolean;
  "aria-describedby": string | undefined;
}

interface TaskFieldProps {
  label: string;
  hint?: string;
  error: string | undefined;
  /** Rend le champ de saisie : il reçoit son `id` et ses attributs d'accessibilité. */
  children: (props: ControlProps) => ReactNode;
}

/** Étiquette, champ, aide et message d'erreur en ligne d'un champ du formulaire d'ajout. */
export function TaskField({ label, hint, error, children }: TaskFieldProps) {
  const id = useId();
  const hintId = useId();
  const errorId = useId();
  const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(" ");
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      {children({
        id,
        "aria-invalid": error !== undefined,
        "aria-describedby": describedBy || undefined,
      })}
      {hint && (
        <p id={hintId} className="text-xs text-muted-foreground">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
