import type { KeyboardEvent } from "react";
import { cn } from "@/shared/lib/utils";
import { fieldClass } from "@/shared/ui/fieldClass";

interface AnswerFieldProps {
  value: string;
  disabled: boolean;
  multiline: boolean;
  maxLength?: number;
  onChange: (value: string) => void;
  /** Ctrl+Entrée (ou Cmd+Entrée) dans la zone de texte. */
  onSend: () => void;
}

/** La saisie d'une réponse libre : une ligne, ou une zone de texte où Entrée va à la ligne et Ctrl+Entrée envoie. */
export function AnswerField({
  value,
  disabled,
  multiline,
  maxLength,
  onChange,
  onSend,
}: AnswerFieldProps) {
  const common = { value, disabled, maxLength, autoFocus: !disabled };
  if (!multiline) {
    return (
      <input
        {...common}
        type="text"
        onChange={(event) => onChange(event.target.value)}
        className={fieldClass}
      />
    );
  }
  const sendWithCtrl = (event: KeyboardEvent) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      onSend();
    }
  };
  return (
    <textarea
      {...common}
      rows={6}
      onKeyDown={sendWithCtrl}
      onChange={(event) => onChange(event.target.value)}
      className={cn(fieldClass, "h-auto min-h-32 py-1.5")}
    />
  );
}
