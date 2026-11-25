import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";

interface FeatureFilterProps {
  /** `""`: all. */
  value: string;
  options: { value: string; label: string }[];
  onChange: (feature: string) => void;
}

/** The feature filter: a native list, « Toutes » first. */
export function FeatureFilter({ value, options, onChange }: FeatureFilterProps) {
  const id = useId();
  return (
    <div className="flex items-center gap-2">
      <label htmlFor={id} className="text-sm font-medium">
        {t("mcp.levels.feature")}
      </label>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={`${fieldClass} w-auto`}
      >
        <option value="">{t("mcp.levels.all")}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
