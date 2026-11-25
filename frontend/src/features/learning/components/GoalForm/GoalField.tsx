import { useId } from "react";
import type { ReactNode } from "react";

interface ControlProps {
  id: string;
  "aria-invalid": boolean;
  "aria-describedby": string;
}

interface GoalFieldProps {
  label: string;
  hint: string;
  error: string | undefined;
  /** Renders the input field: it receives its `id` and its accessibility attributes. */
  children: (props: ControlProps) => ReactNode;
}

/** Label, input, help and error message of a goal form field. */
export function GoalField({ label, hint, error, children }: GoalFieldProps) {
  const id = useId();
  const hintId = useId();
  const errorId = useId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      {children({
        id,
        "aria-invalid": error !== undefined,
        "aria-describedby": error ? `${hintId} ${errorId}` : hintId,
      })}
      <p id={hintId} className="text-xs text-muted-foreground">
        {hint}
      </p>
      {error ? (
        <p id={errorId} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}
