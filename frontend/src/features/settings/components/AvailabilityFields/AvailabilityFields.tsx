import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { formatMinutes } from "@/shared/lib/format";
import { errorHint } from "../errorHint";
import { MINUTES_RANGE } from "../ranges";
import { NumberField } from "../NumberField";
import type { AvailabilityFlags, AvailabilityKey, AvailabilityValues } from "../viewTypes";

interface AvailabilityFieldsProps {
  values: AvailabilityValues;
  flags: AvailabilityFlags;
  /** Fields the server rejected on the last save. */
  refused?: Partial<Record<AvailabilityKey, boolean>>;
  /** Calculated weekly budget, in minutes; `null` while a duration is invalid. */
  budget: number | null;
  onChange: (key: AvailabilityKey, value: string) => void;
}

const FIELDS = [
  { key: "weekday", label: "settings.availability.weekday" },
  { key: "weekendMin", label: "settings.availability.weekendMin" },
  { key: "weekendMax", label: "settings.availability.weekendMax" },
] as const;

/** Is the entered value outside the bounds (empty or non-whole included)? */
function outOfBounds(text: string): boolean {
  const value = Number(text);
  return (
    text.trim() === "" ||
    !Number.isInteger(value) ||
    value < MINUTES_RANGE.min ||
    value > MINUTES_RANGE.max
  );
}

/**
 * Weekday minutes, weekend block (minimum and maximum) and the weekly budget derived
 * from them.
 */
export function AvailabilityFields({
  values,
  flags,
  refused = {},
  budget,
  onChange,
}: AvailabilityFieldsProps) {
  const orderId = useId();
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-6">
        {FIELDS.map(({ key, label }) => (
          <NumberField
            key={key}
            label={t(label)}
            value={values[key]}
            {...MINUTES_RANGE}
            invalid={flags[key]}
            // A field marked only for the order of the bounds has a value within them: its
            // help text must not say « Erreur » (the order message says that).
            hintError={refused[key] || (flags[key] && outOfBounds(values[key]))}
            refused={refused[key]}
            describedBy={flags.weekendOrder && key !== "weekday" ? orderId : undefined}
            onChange={(value) => onChange(key, value)}
          />
        ))}
      </div>
      {flags.weekendOrder ? (
        <p id={orderId} className="text-sm text-destructive">
          {errorHint(true, t("settings.availability.weekendOrder"))}
        </p>
      ) : null}
      <p className="text-sm">
        <strong className="font-medium">
          {budget === null
            ? t("settings.availability.budgetInvalid")
            : t("settings.availability.budget", { total: formatMinutes(budget) })}
        </strong>
        <span className="block text-muted-foreground">{t("settings.availability.budgetHint")}</span>
      </p>
    </div>
  );
}
