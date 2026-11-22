import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { TrainingMode } from "../../trainingApi";
import { ModeSelect } from "./ModeSelect";

export function TrainingStart({
  busy,
  onStart,
}: {
  busy: boolean;
  onStart: (mode: TrainingMode) => void;
}) {
  const [mode, setMode] = useState<TrainingMode>("socratic");
  return (
    <form
      className="flex max-w-xl flex-col items-start gap-4 rounded-xl border border-border p-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (!busy) onStart(mode);
      }}
    >
      <p className="text-sm text-muted-foreground">{t("training.startHint")}</p>
      <ModeSelect mode={mode} onChange={setMode} disabled={busy} />
      <Button type="submit" disabled={busy}>
        {t("training.start")}
      </Button>
    </form>
  );
}
