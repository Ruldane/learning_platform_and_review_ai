import { useId, type Ref } from "react";
import { fieldClass } from "@/shared/ui/fieldClass";

interface FolderFieldProps {
  label: string;
  maxLength: number;
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
  inputRef?: Ref<HTMLInputElement>;
}

export function FolderField({
  label,
  maxLength,
  value,
  disabled,
  onChange,
  inputRef,
}: FolderFieldProps) {
  const id = useId();
  return (
    <label htmlFor={id} className="flex flex-col gap-1 text-sm">
      {label}
      <input
        required
        id={id}
        ref={inputRef}
        className={fieldClass}
        maxLength={maxLength}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
