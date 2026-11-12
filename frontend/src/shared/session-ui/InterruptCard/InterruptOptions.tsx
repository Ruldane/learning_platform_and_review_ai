import type { InterruptPayload } from "@/shared/realtime/types";
import { Button } from "@/shared/ui/button";

type InterruptOption = NonNullable<InterruptPayload["options"]>[number];

interface InterruptOptionsProps {
  options: InterruptOption[];
  labelledBy: string;
  disabled: boolean;
  /** Le premier bouton prend le focus (jamais quand des champs de saisie passent avant). */
  autoFocusFirst: boolean;
  onPick: (value: string) => void;
}

/** Les options d'une question : un bouton chacune, qui envoie sa valeur. */
export function InterruptOptions({
  options,
  labelledBy,
  disabled,
  autoFocusFirst,
  onPick,
}: InterruptOptionsProps) {
  return (
    <div role="group" aria-labelledby={labelledBy} className="mt-2 flex flex-wrap gap-2">
      {options.map((option, index) => (
        <Button
          key={option.value}
          variant="outline"
          disabled={disabled}
          autoFocus={!disabled && autoFocusFirst && index === 0}
          onClick={() => onPick(option.value)}
        >
          {option.label}
        </Button>
      ))}
    </div>
  );
}
