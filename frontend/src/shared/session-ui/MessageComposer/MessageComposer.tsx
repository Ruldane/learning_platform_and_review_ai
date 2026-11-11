import { useState, type FormEvent, type KeyboardEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import { cn } from "@/shared/lib/utils";

interface MessageComposerProps {
  disabled: boolean;
  onSend: (text: string) => void;
}

/** Champ de message : Entrée envoie, Maj+Entrée ajoute un retour à la ligne. */
export function MessageComposer({ disabled, onSend }: MessageComposerProps) {
  const [text, setText] = useState("");

  const send = () => {
    const message = text.trim();
    if (disabled || message === "") return;
    onSend(message);
    setText("");
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    // Pendant une composition (IME), Entrée valide le texte saisi et n'envoie pas.
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
    event.preventDefault();
    send();
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    send();
  };

  return (
    <form onSubmit={onSubmit} className="flex items-end gap-2">
      <label className="flex-1">
        <span className="sr-only">{t("session.composer.label")}</span>
        <textarea
          value={text}
          rows={2}
          disabled={disabled}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKeyDown}
          className={cn(fieldClass, "h-auto resize-y py-1.5")}
        />
      </label>
      <Button type="submit" disabled={disabled || text.trim() === ""}>
        {t("session.composer.send")}
      </Button>
    </form>
  );
}
