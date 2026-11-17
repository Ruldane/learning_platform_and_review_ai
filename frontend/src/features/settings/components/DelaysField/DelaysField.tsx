import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";

/** Bornes du contrat : de 1 à 90 jours. */
const RANGE = { min: 1, max: 90 } as const;
const LABELS = [
  "settings.availability.delays.first",
  "settings.availability.delays.second",
  "settings.availability.delays.third",
] as const;

type Delays = [string, string, string];

interface DelaysFieldProps {
  /** Les trois délais, en jours, tels que saisis. */
  value: Delays;
  /** Hors bornes ou pas strictement croissants. */
  invalid: boolean;
  /** Refusé par le serveur : la valeur n'est jamais citée. */
  refused?: boolean;
  onChange: (index: 0 | 1 | 2, value: string) => void;
}

/** Les délais des trois relances : trois nombres de jours strictement croissants. */
export function DelaysField({ value, invalid, refused = false, onChange }: DelaysFieldProps) {
  const legendId = useId();
  const hintId = useId();
  const bad = invalid || refused;
  const hint =
    refused && !invalid
      ? t("settings.fields.refused")
      : t("settings.availability.delays.hint", RANGE);
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
              min={RANGE.min}
              max={RANGE.max}
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
