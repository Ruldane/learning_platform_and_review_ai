import type { InputHTMLAttributes } from "react";
import { fieldClass } from "@/shared/ui/fieldClass";
import { GoalField } from "./GoalField";

interface GoalInputFieldProps {
  label: string;
  hint: string;
  error: string | undefined;
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
  /** Field-specific settings (type, range, input mode). */
  input?: InputHTMLAttributes<HTMLInputElement>;
}

/** A one-line input of the goal form, with its help and error. */
export function GoalInputField({
  label,
  hint,
  error,
  value,
  disabled,
  onChange,
  input,
}: GoalInputFieldProps) {
  return (
    <GoalField label={label} hint={hint} error={error}>
      {(props) => (
        <input
          {...props}
          {...input}
          value={value}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
          className={fieldClass}
        />
      )}
    </GoalField>
  );
}
