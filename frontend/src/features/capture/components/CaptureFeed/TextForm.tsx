import { useId, useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import { MAX_TEXT } from "../source";
import type { QuestionView } from "../viewTypes";

const FIELD = "text";
const CANCEL = "cancel";

interface TextFormProps {
  interrupt: QuestionView;
  disabled: boolean;
  onAnswer: (value: unknown) => void;
}

/** La zone de texte (taille et libellé du contrat), « Envoyer le texte » et « Abandonner ». */
export function TextForm({ interrupt, disabled, onAnswer }: TextFormProps) {
  const id = useId();
  const [text, setText] = useState("");
  const field = interrupt.fields?.find((item) => item.id === FIELD);
  const max = field?.max_length ?? MAX_TEXT;
  const cancel = interrupt.options?.find((option) => option.value === CANCEL);
  const ready = text.trim() !== "";

  const send = (event: FormEvent) => {
    event.preventDefault();
    if (!disabled && ready) onAnswer({ answers: { [FIELD]: text.trim() } });
  };

  return (
    <form onSubmit={send} className="mt-2 flex flex-col gap-2">
      <label htmlFor={id} className="text-sm font-medium">
        {field?.label ?? t("capture.input.label")}
      </label>
      <textarea
        id={id}
        rows={6}
        autoFocus={!disabled}
        value={text}
        maxLength={max}
        disabled={disabled}
        onChange={(event) => setText(event.target.value)}
        className={cn(fieldClass, "h-auto min-h-32 py-1.5")}
      />
      <p className="text-xs text-muted-foreground">
        {t("capture.textCard.count", { count: text.length, max })}
      </p>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={disabled || !ready}>
          {t("capture.textCard.send")}
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={disabled}
          onClick={() => onAnswer(cancel?.value ?? CANCEL)}
        >
          {cancel?.label ?? t("capture.textCard.cancel")}
        </Button>
      </div>
    </form>
  );
}
