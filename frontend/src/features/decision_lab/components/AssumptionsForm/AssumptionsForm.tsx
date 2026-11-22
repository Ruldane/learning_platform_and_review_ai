import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { AssumptionFields } from "../viewTypes";
import { ArchitectureFields } from "../ArchitectureFields";
import { NumberField } from "../NumberField";

const WORKLOAD = [
  ["rate", "decisionLab.load", 0, 100_000],
  ["duration", "decisionLab.duration", 1, 1440],
  ["outage", "decisionLab.outage", 0, 1440],
] as const;
const ARCHITECTURES = [
  ["first", "decisionLab.architectureA"],
  ["second", "decisionLab.architectureB"],
] as const;

interface Props {
  value: AssumptionFields;
  onChange: (value: AssumptionFields) => void;
  onCompare: () => void;
  busy: boolean;
}

export function AssumptionsForm({ value, onChange, onCompare, busy }: Props) {
  return (
    <form className="flex flex-col gap-4" onSubmit={(event) => { event.preventDefault(); onCompare(); }}>
      <fieldset className="grid gap-3 rounded-lg border border-border px-4 pb-4 pt-2 md:grid-cols-3">
        <legend className="px-1 font-semibold">{t("decisionLab.workload")}</legend>
        {WORKLOAD.map(([key, labelKey, min, max]) => (
          <NumberField
            key={key}
            label={t(labelKey)}
            value={value[key]}
            min={min}
            max={key === "outage" && value.duration ? value.duration : max}
            onChange={(number) => onChange({ ...value, [key]: number })}
          />
        ))}
      </fieldset>
      <div className="grid gap-4 md:grid-cols-2">
        {ARCHITECTURES.map(([key, labelKey]) => (
          <ArchitectureFields
            key={key}
            label={t(labelKey)}
            value={value[key]}
            onChange={(architecture) => onChange({ ...value, [key]: architecture })}
          />
        ))}
      </div>
      <Button type="submit" className="self-start" disabled={busy}>{t("decisionLab.compare")}</Button>
    </form>
  );
}
