import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";

interface Props {
  busy: boolean;
  onStart: (question: string) => void;
}

export function DebateQuestion({ busy, onStart }: Props) {
  const [draft, setDraft] = useState("");
  const question = draft.trim();
  const disabled = !question || busy;
  return (
    <form
      className="flex flex-col items-start gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (!disabled) onStart(question);
      }}
    >
      <label htmlFor="debate-question" className="font-medium">
        {t("expertDebates.question")}
      </label>
      <p id="debate-research-hint" className="text-sm text-muted-foreground">
        {t("expertDebates.researchHint")}
      </p>
      <textarea
        id="debate-question"
        aria-describedby="debate-research-hint"
        rows={4}
        maxLength={2000}
        value={draft}
        readOnly={busy}
        className={`${fieldClass} h-auto`}
        onChange={(event) => setDraft(event.currentTarget.value)}
      />
      <Button type="submit" aria-disabled={disabled}>
        {t("expertDebates.start")}
      </Button>
    </form>
  );
}
