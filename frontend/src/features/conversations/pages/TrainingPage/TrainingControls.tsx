import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { TrainingChange, TrainingMode } from "../../trainingApi";
import { ModeSelect } from "./ModeSelect";

export function TrainingControls({ mode, saving, busy, onChange }: {
  mode: TrainingMode;
  saving: boolean;
  busy: boolean;
  onChange: (body: TrainingChange) => void;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <ModeSelect mode={mode} disabled={saving} onChange={(next) => onChange({ action: "mode", mode: next })} />
      <Button type="button" variant="outline" disabled={saving || busy}
        onClick={() => onChange({ action: "finish" })}>
        {t("training.finish")}
      </Button>
    </div>
  );
}
