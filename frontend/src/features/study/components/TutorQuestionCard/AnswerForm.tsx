import { useState, type FormEvent, type KeyboardEvent } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import { mergeVoiceDraft, VoiceDraftControls } from "@/shared/voice";

/** Same cap as the `answer` field of the interruption on the back end. */
const MAX_ANSWER_LENGTH = 4000;

interface AnswerFormProps {
  disabled: boolean;
  stuckLabel: string;
  skipLabel: string;
  onSubmit: (text: string) => void;
  onStuck: () => void;
  onSkip: () => void;
}

function submitShortcut(event: KeyboardEvent, submit: (event: FormEvent) => void) {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) submit(event);
}

/** Answer field (Ctrl or Cmd + Enter sends); buttons « Répondre », « Je bloque », « Passer ». */
export function AnswerForm({
  disabled,
  stuckLabel,
  skipLabel,
  onSubmit,
  onStuck,
  onSkip,
}: AnswerFormProps) {
  const [draft, setDraft] = useState("");
  const value = draft.trim();
  const canSend = !disabled && value !== "";

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (canSend) onSubmit(value);
  };

  return (
    <form onSubmit={submit} className="mt-2 flex flex-col gap-2">
      <label className="flex flex-col gap-1">
        <span className="sr-only">{t("study.tutor.answerLabel")}</span>
        <textarea
          value={draft}
          disabled={disabled}
          autoFocus={!disabled}
          maxLength={MAX_ANSWER_LENGTH}
          rows={3}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => submitShortcut(event, submit)}
          className={cn(fieldClass, "h-auto min-h-20 py-1.5")}
        />
      </label>
      {!disabled && (
        <VoiceDraftControls
          onDraft={(text) => setDraft((old) => mergeVoiceDraft(old, text, MAX_ANSWER_LENGTH))}
        />
      )}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={!canSend}>
          {t("study.tutor.answer")}
        </Button>
        <Button type="button" variant="outline" disabled={disabled} onClick={onStuck}>
          {stuckLabel}
        </Button>
        <Button type="button" variant="outline" disabled={disabled} onClick={onSkip}>
          {skipLabel}
        </Button>
      </div>
    </form>
  );
}
