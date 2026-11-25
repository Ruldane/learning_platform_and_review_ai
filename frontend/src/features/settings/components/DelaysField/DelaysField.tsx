import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import { errorHint } from "../errorHint";
import { DELAY_RANGE } from "../ranges";

const LABELS = [
  "settings.availability.delays.first",
  "settings.availability.delays.second",
  "settings.availability.delays.third",
] as const;

type Delays = [string, string, string];

interface DelaysFieldProps {
  /** The three delays, in days, as typed. */
  value: Delays;
  /** Out of bounds or not strictly increasing. */
  invalid: boolean;
  /** Refused by the server: the value is never quoted. */
  refused?: boolean;
  onChange: (index: 0 | 1 | 2, value: string) => void;
}

/** The delays of the three reminders: three strictly increasing day counts. */
export function DelaysField({ value, invalid, refused = false, onChange }: DelaysFieldProps) {
  const legendId = useId();
  const hintId = useId();
  const bad = invalid || refused;
  const hint = errorHint(
    bad,
    refused && !invalid
      ? t("settings.fields.refused")
      : t("settings.availability.delays.hint", DELAY_RANGE),
  );
  return (
    <div role="group" aria-labelledby={legendId} className="flex flex-col gap-1">
      <span id={legendId} className="text-sm font-medium">
        {t("settings.availability.delays.label")}
      </span>
      <div className="flex flex-wrap gap-4">
        {LABELS.map((key, index) => (
          <label key={key} className="text-sm">
            {t(key)}
            <input
              type="number"
              inputMode="numeric"
              min={DELAY_RANGE.min}
              max={DELAY_RANGE.max}
              step={1}
              value={value[index] ?? ""}
              aria-invalid={bad}
              aria-describedby={hintId}
              onChange={(event) => onChange(index as 0 | 1 | 2, event.target.value)}
              className={`${fieldClass} mt-1 block max-w-32`}
            />
          </label>
        ))}
      </div>
      <p id={hintId} className={bad ? "text-sm text-destructive" : "text-sm text-muted-foreground"}>
        {hint}
      </p>
    </div>
  );
}
