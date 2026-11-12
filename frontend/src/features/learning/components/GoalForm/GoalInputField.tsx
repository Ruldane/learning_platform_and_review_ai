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
  /** Réglages propres au champ (type, plage, mode de saisie). */
  input?: InputHTMLAttributes<HTMLInputElement>;
}

/** Un champ de saisie d'une ligne du formulaire d'objectif, avec son aide et son erreur. */
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
