import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { TrainingChange, TrainingSession } from "../../trainingApi";
import { ModeSelect } from "./ModeSelect";
import { TrainingLessons } from "./TrainingLessons";

export function TrainingControls({
  session,
  saving,
  busy,
  onChange,
}: {
  session: TrainingSession;
  saving: boolean;
  busy: boolean;
  onChange: (body: TrainingChange) => void;
}) {
  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <ModeSelect
          mode={session.mode}
          disabled={saving}
          onChange={(mode) => onChange({ action: "mode", mode })}
        />
        {session.status === "open" ? (
          <Button
            type="button"
            variant="outline"
            disabled={saving || busy}
            onClick={() => onChange({ action: "finish" })}
          >
            {t("training.finish")}
          </Button>
        ) : null}
      </div>
      <TrainingLessons
        ids={session.lesson_ids ?? []}
        busy={busy || saving}
        onChange={(lesson_ids) => onChange({ action: "lessons", lesson_ids })}
      />
    </>
  );
}
