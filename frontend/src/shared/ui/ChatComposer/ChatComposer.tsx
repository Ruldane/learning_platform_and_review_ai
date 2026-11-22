import { useId, useState, type KeyboardEvent, type ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";

interface ChatComposerProps {
  busy: boolean;
  label: string;
  placeholder: string;
  initialText?: string;
  actions?: ReactNode;
  /** Rend `true` quand la question est partie : la saisie n'est vidée que dans ce cas. */
  onSend: (question: string) => Promise<boolean>;
}

function submitOnEnter(event: KeyboardEvent, submit: () => Promise<void>) {
  if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
  event.preventDefault();
  void submit();
}

/**
 * Entrée envoie, Maj+Entrée fait un retour à la ligne. Une question refusée ou en erreur reste
 * dans la zone de texte.
 */
export function ChatComposer({
  busy,
  label,
  placeholder,
  initialText = "",
  actions,
  onSend,
}: ChatComposerProps) {
  const fieldId = useId();
  const [text, setText] = useState(initialText);
  const question = text.trim();
  const submit = async () => {
    if (question === "" || busy) return;
    if (await onSend(question)) setText("");
  };
  return (
    <form
      className="flex flex-col gap-2 border-t border-border p-3"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      {actions}
      <label htmlFor={fieldId} className="sr-only">
        {label}
      </label>
      <textarea
        id={fieldId}
        rows={2}
        value={text}
        maxLength={2000}
        placeholder={placeholder}
        aria-describedby={`${fieldId}-help`}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => submitOnEnter(event, submit)}
        className={cn(fieldClass, "h-auto resize-none py-1.5")}
      />
      <div className="flex items-center justify-between gap-2">
        <p id={`${fieldId}-help`} className="text-xs text-muted-foreground">
          {t("chat.shortcuts")}
        </p>
        <Button type="submit" size="sm" disabled={question === "" || busy}>
          {t("chat.send")}
        </Button>
      </div>
    </form>
  );
}
