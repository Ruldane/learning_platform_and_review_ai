import { fieldClass } from "@/shared/ui/fieldClass";
import { TaskField } from "./TaskField";

interface TaskTextFieldProps {
  label: string;
  hint?: string;
  error: string | undefined;
  value: string;
  disabled: boolean;
  inputMode?: "numeric";
  onChange: (value: string) => void;
}

/** Input field of one row of the add form, with its label, help and error. */
export function TaskTextField({
  label,
  hint,
  error,
  value,
  disabled,
  inputMode,
  onChange,
}: TaskTextFieldProps) {
  return (
    <TaskField label={label} hint={hint} error={error}>
      {(aria) => (
        <input
          {...aria}
          inputMode={inputMode}
          value={value}
          disabled={disabled}
          className={fieldClass}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
    </TaskField>
  );
}
