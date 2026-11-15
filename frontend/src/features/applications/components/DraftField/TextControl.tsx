import { cn } from "@/shared/lib/utils";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { FieldControlProps } from "../Field";
import type { FieldSpec } from "./DraftField";

interface TextControlProps {
  control: FieldControlProps;
  spec: FieldSpec;
  value: string;
  disabled?: boolean;
  autoFocus?: boolean;
  onChange: (value: string) => void;
}

/** Le champ natif d'une saisie libre : zone de texte pour `textarea`, sinon `input` (texte, lien, date). */
export function TextControl({
  control,
  spec,
  value,
  disabled,
  autoFocus,
  onChange,
}: TextControlProps) {
  const { kind, maxLength, required, max } = spec;
  const common = { ...control, value, disabled, autoFocus, required };
  const change = (event: { target: { value: string } }) => onChange(event.target.value);
  if (kind === "textarea") {
    return (
      <textarea
        {...common}
        rows={3}
        maxLength={maxLength ?? 2000}
        onChange={change}
        className={cn(fieldClass, "h-auto min-h-16 py-1.5")}
      />
    );
  }
  return (
    <input
      {...common}
      type={kind}
      maxLength={maxLength}
      max={max}
      onChange={change}
      className={fieldClass}
    />
  );
}
