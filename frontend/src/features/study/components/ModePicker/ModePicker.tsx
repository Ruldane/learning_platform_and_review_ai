import { useId } from "react";
import { t } from "@/shared/i18n/t";
import type { StudyModeView } from "../viewTypes";

const MODES: StudyModeView[] = ["socratic", "feynman", "direct"];

interface ModePickerProps {
  value: StudyModeView;
  onChange: (mode: StudyModeView) => void;
}

/** Choix du mode d'étude : trois boutons radio, chacun avec sa description. */
export function ModePicker({ value, onChange }: ModePickerProps) {
  const id = useId();
  return (
    <div className="flex flex-col gap-2">
      <p id={`${id}-legend`} className="text-sm font-medium">
        {t("study.modes.label")}
      </p>
      <div role="radiogroup" aria-labelledby={`${id}-legend`} className="grid gap-2 sm:grid-cols-3">
        {MODES.map((mode) => (
          <label
            key={mode}
            className="flex cursor-pointer items-start gap-2 rounded-xl border bg-card p-3 has-[:checked]:border-primary has-[:checked]:ring-1 has-[:checked]:ring-primary has-[:focus-visible]:ring-3 has-[:focus-visible]:ring-ring"
          >
            <input
              type="radio"
              name={id}
              value={mode}
              checked={value === mode}
              onChange={() => onChange(mode)}
              aria-labelledby={`${id}-${mode}-label`}
              aria-describedby={`${id}-${mode}-description`}
              className="mt-1"
            />
            <span className="flex flex-col gap-0.5">
              <span id={`${id}-${mode}-label`} className="font-medium">
                {t(`study.modes.${mode}.label`)}
              </span>
              <span id={`${id}-${mode}-description`} className="text-sm text-muted-foreground">
                {t(`study.modes.${mode}.description`)}
              </span>
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}
