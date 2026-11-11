import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";

interface FreeTextAnswerProps {
  disabled: boolean;
  onSubmit: (value: string) => void;
}

/** Champ de réponse libre d'une interruption : Entrée ou « Répondre » envoie, une réponse vide est refusée. */
export function FreeTextAnswer({ disabled, onSubmit }: FreeTextAnswerProps) {
  const [draft, setDraft] = useState("");
  const value = draft.trim();

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!disabled && value !== "") onSubmit(value);
  };

  return (
    <form onSubmit={submit} className="mt-2 flex items-end gap-2">
      <label className="flex-1">
        <span className="sr-only">{t("session.interrupt.answerLabel")}</span>
        <input
          type="text"
          value={draft}
          disabled={disabled}
          autoFocus={!disabled}
          onChange={(event) => setDraft(event.target.value)}
          className={fieldClass}
        />
      </label>
      <Button type="submit" disabled={disabled || value === ""}>
        {t("session.interrupt.answer")}
      </Button>
    </form>
  );
}
