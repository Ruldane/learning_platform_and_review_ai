import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";

interface FilterSelectProps {
  label: string;
  /** `null` : tous. */
  value: string | null;
  options: { value: string; label: string }[];
  onChange: (value: string | null) => void;
}

/** Une liste native avec « Tous » en tête : le clavier et les lecteurs d'écran l'ont d'office. */
export function FilterSelect({ label, value, options, onChange }: FilterSelectProps) {
  const id = useId();
  return (
    <div className="flex items-center gap-2">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <select
        id={id}
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value === "" ? null : event.target.value)}
        className={`${fieldClass} w-auto`}
      >
        <option value="">{t("costs.log.filters.all")}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
