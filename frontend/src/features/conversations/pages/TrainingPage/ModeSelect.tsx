import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { TrainingMode } from "../../trainingApi";

const MODES = ["socratic", "feynman", "direct"] as const satisfies readonly TrainingMode[];

interface ModeSelectProps {
  mode: TrainingMode;
  disabled?: boolean;
  onChange: (mode: TrainingMode) => void;
}

export function ModeSelect({ mode, onChange, disabled }: ModeSelectProps) {
  const id = useId();
  return (
    <label htmlFor={id} className="flex max-w-80 flex-col gap-1 text-sm">
      {t("training.mode")}
      <select
        id={id}
        className={fieldClass}
        value={mode}
        disabled={disabled}
        onChange={(event) => {
          const next = MODES.find((choice) => choice === event.target.value);
          if (next) onChange(next);
        }}
      >
        {MODES.map((choice) => (
          <option value={choice} key={choice}>
            {t(`study.modes.${choice}.label`)}
          </option>
        ))}
      </select>
    </label>
  );
}
