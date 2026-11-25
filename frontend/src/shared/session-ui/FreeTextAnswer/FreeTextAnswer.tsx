import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { mergeVoiceDraft, VoiceDraftControls } from "@/shared/voice";
import { AnswerField } from "./AnswerField";

interface FreeTextAnswerProps {
  disabled: boolean;
  onSubmit: (value: string) => void;
  /** A long written answer: a text area (Enter adds a line, Ctrl+Enter sends). */
  multiline?: boolean;
  /** Maximum number of characters. */
  maxLength?: number;
  /** Name of the field read by screen readers; « Ta réponse » by default. */
  label?: string;
  voice?: boolean;
}

/** Free-text answer field: Enter or « Répondre » sends; an empty answer is refused. */
export function FreeTextAnswer({
  disabled,
  onSubmit,
  multiline = false,
  maxLength,
  label,
  voice = false,
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
      className={cn("mt-2 flex flex-wrap gap-2", multiline ? "flex-col items-start" : "items-end")}
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
      {voice && !disabled && (
        <VoiceDraftControls
          onDraft={(text) => setDraft((old) => mergeVoiceDraft(old, text, maxLength))}
        />
      )}
    </form>
  );
}
