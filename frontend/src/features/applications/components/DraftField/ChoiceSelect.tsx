import { fieldClass } from "@/shared/ui/fieldClass";
import type { FieldControlProps } from "../Field";

export interface ChoiceView {
  value: string;
  label: string;
}

interface ChoiceSelectProps {
  control: FieldControlProps;
  value: string;
  choices: ChoiceView[];
  disabled?: boolean;
  onChange: (value: string) => void;
}

/** A native dropdown linked to its label (`control`). */
export function ChoiceSelect({ control, value, choices, disabled, onChange }: ChoiceSelectProps) {
  return (
    <select
      {...control}
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
      className={fieldClass}
    >
      {choices.map((choice) => (
        <option key={choice.value} value={choice.value}>
          {choice.label}
        </option>
      ))}
    </select>
  );
}
