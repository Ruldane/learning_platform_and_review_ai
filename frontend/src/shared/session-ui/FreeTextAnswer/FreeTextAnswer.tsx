import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { AnswerField } from "./AnswerField";

interface FreeTextAnswerProps {
  disabled: boolean;
  onSubmit: (value: string) => void;
  /** Une réponse écrite longue : une zone de texte (Entrée va à la ligne, Ctrl+Entrée envoie). */
  multiline?: boolean;
  /** Nombre de caractères au plus. */
  maxLength?: number;
  /** Nom du champ lu aux lecteurs d'écran ; « Ta réponse » par défaut. */
  label?: string;
}

/** Champ de réponse libre d'une interruption : Entrée ou « Répondre » envoie, une réponse vide est refusée. */
export function FreeTextAnswer({
  disabled,
  onSubmit,
  multiline = false,
  maxLength,
  label,
}: FreeTextAnswerProps) {
  const [draft, setDraft] = useState("");
  const value = draft.trim();

  const send = () => {
    if (!disabled && value !== "") onSubmit(value);
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    send();
  };

  return (
    <form
      onSubmit={submit}
      className={cn("mt-2 flex gap-2", multiline ? "flex-col items-start" : "items-end")}
    >
      <label className={multiline ? "w-full" : "flex-1"}>
        <span className="sr-only">{label ?? t("session.interrupt.answerLabel")}</span>
        <AnswerField
          value={draft}
          disabled={disabled}
          multiline={multiline}
          maxLength={maxLength}
          onChange={setDraft}
          onSend={send}
        />
      </label>
      <Button type="submit" disabled={disabled || value === ""}>
        {t("session.interrupt.answer")}
      </Button>
    </form>
  );
}
