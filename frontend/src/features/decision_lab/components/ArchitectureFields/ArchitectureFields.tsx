import { t } from "@/shared/i18n/t";
import type { ArchitectureFieldsValue } from "../viewTypes";
import { NumberField } from "../NumberField";

const NUMBERS = [
  ["replicas", "decisionLab.replicas", 1, 64],
  ["capacityPerReplica", "decisionLab.capacity", 1, 100_000],
  ["hourlyCents", "decisionLab.price", 0, 100_000],
] as const;

interface Props {
  label: string;
  value: ArchitectureFieldsValue;
  onChange: (value: ArchitectureFieldsValue) => void;
}

export function ArchitectureFields({ label, value, onChange }: Props) {
  return (
    <fieldset className="flex flex-col gap-3 rounded-lg border border-border px-4 pb-4 pt-2">
      <legend className="px-1 font-semibold">{label}</legend>
      {NUMBERS.map(([key, labelKey, min, max]) => (
        <NumberField
          key={key}
          label={t(labelKey)}
          value={value[key]}
          min={min}
          max={max}
          onChange={(number) => onChange({ ...value, [key]: number })}
        />
      ))}
    </fieldset>
  );
}
