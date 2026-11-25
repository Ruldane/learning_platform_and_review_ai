import { useId } from "react";
import { fieldClass } from "@/shared/ui/fieldClass";

interface ModelFieldProps {
  /** Label read by screen readers (the field has no visible text). */
  label: string;
  /** Models offered, or `null` for free-text entry. */
  models: string[] | null;
  /** Model in effect (free text: empty while a new model is expected). */
  value: string;
  disabled?: boolean;
  /** Id of a help text describing the field (e.g. « Saisis le modèle, puis Entrée »). */
  describedBy?: string;
  /**
   * List: on each choice. Free text: on blur or Enter, once per entry.
   */
  onCommit: (model: string) => void;
}

/** A level's model: a dropdown, or a text field when the provider has no list. */
export function ModelField({
  label,
  models,
  value,
  disabled = false,
  describedBy,
  onCommit,
}: ModelFieldProps) {
  const id = useId();
  return (
    <>
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      {models ? (
        <select
          id={id}
          className={`${fieldClass} sm:max-w-64`}
          value={value}
          disabled={disabled}
          aria-describedby={describedBy}
          onChange={(event) => onCommit(event.target.value)}
        >
          {models.includes(value) ? null : <option value={value}>{value}</option>}
          {models.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>
      ) : (
        <input
          // The key resets the field when the saved value changes.
          key={value}
          id={id}
          type="text"
          className={`${fieldClass} sm:max-w-64`}
          defaultValue={value}
          disabled={disabled}
          aria-describedby={describedBy}
          spellCheck={false}
          onBlur={(event) => onCommit(event.currentTarget.value)}
          onKeyDown={(event) => {
            // Enter commits, like losing focus (one path only: onBlur).
            if (event.key === "Enter") event.currentTarget.blur();
          }}
        />
      )}
    </>
  );
}
