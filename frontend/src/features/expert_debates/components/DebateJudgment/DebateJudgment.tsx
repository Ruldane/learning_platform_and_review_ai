import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";

interface Props {
  judgment: string | null;
  saving: boolean;
  onSave: (text: string) => void;
}

export function DebateJudgment({ judgment, saving, onSave }: Props) {
  const [draft, setDraft] = useState<string | null>(null);
  const text = draft ?? judgment ?? "";
  const stored = Boolean(judgment && text.trim() === judgment);
  const disabled = stored || saving || !text.trim();
  return (
    <form
      className="flex flex-col items-start gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (!disabled) onSave(text.trim());
      }}
    >
      <label htmlFor="debate-judgment" className="text-xl font-semibold">
        {t("expertDebates.judgment")}
      </label>
      <p id="debate-judgment-hint" className="text-sm text-muted-foreground">
        {t("expertDebates.judgmentHint")}
      </p>
      <textarea
        id="debate-judgment"
        aria-describedby="debate-judgment-hint"
        rows={5}
        maxLength={4000}
        value={text}
        readOnly={saving}
        className={`${fieldClass} h-auto`}
        onChange={(event) => setDraft(event.currentTarget.value)}
      />
      <Button type="submit" aria-disabled={disabled}>
        {t("expertDebates.save")}
      </Button>
      {stored && <p role="status">{t("expertDebates.saved")}</p>}
    </form>
  );
}
