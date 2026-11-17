import { t } from "@/shared/i18n/t";
import { formatMinutes } from "@/shared/lib/format";
import { NumberField } from "../NumberField";
import type { AvailabilityFlags, AvailabilityKey, AvailabilityValues } from "../viewTypes";

/** Bornes du contrat : de 0 à 1 440 minutes (une journée). */
const RANGE = { min: 0, max: 1440 } as const;

interface AvailabilityFieldsProps {
  values: AvailabilityValues;
  flags: AvailabilityFlags;
  /** Champs que le serveur a refusés au dernier enregistrement. */
  refused?: Partial<Record<AvailabilityKey, boolean>>;
  /** Budget hebdomadaire calculé, en minutes ; `null` tant qu'une durée est invalide. */
  budget: number | null;
  onChange: (key: AvailabilityKey, value: string) => void;
}

const FIELDS = [
  { key: "weekday", label: "settings.availability.weekday" },
  { key: "weekendMin", label: "settings.availability.weekendMin" },
  { key: "weekendMax", label: "settings.availability.weekendMax" },
] as const;

/** Minutes en semaine, bloc du week-end (minimum et maximum) et le budget hebdomadaire qui en découle. */
export function AvailabilityFields({
  values,
  flags,
  refused = {},
  budget,
  onChange,
}: AvailabilityFieldsProps) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-6">
        {FIELDS.map(({ key, label }) => (
          <NumberField
            key={key}
            label={t(label)}
            value={values[key]}
            {...RANGE}
            invalid={flags[key]}
            refused={refused[key]}
            onChange={(value) => onChange(key, value)}
          />
        ))}
      </div>
      {flags.weekendOrder ? (
        <p className="text-sm text-destructive">{t("settings.availability.weekendOrder")}</p>
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
