import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";

interface DurationFieldProps {
  label: string;
  value: string;
  range: { min: number; max: number };
  invalid: boolean;
  onChange: (value: string) => void;
}

/** Une durée en minutes entières, avec ses bornes dites sous le champ (rouges quand elles sont dépassées). */
export function DurationField({ label, value, range, invalid, onChange }: DurationFieldProps) {
  const hintId = useId();
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium">
        {label}
        <input
          type="number"
          inputMode="numeric"
          min={range.min}
          max={range.max}
          step={1}
          value={value}
          aria-invalid={invalid}
          aria-describedby={hintId}
          onChange={(event) => onChange(event.target.value)}
          className={`${fieldClass} mt-1 max-w-32`}
        />
      </label>
      <p
        id={hintId}
        className={invalid ? "text-sm text-destructive" : "text-sm text-muted-foreground"}
      >
        {t("settings.study.range", range)}
      </p>
    </div>
  );
}
