import { fieldClass } from "@/shared/ui/fieldClass";

interface FilterSelectProps {
  label: string;
  value: string | null;
  allLabel: string;
  options: { value: string; label: string }[];
  onChange: (value: string | null) => void;
}

/** Une liste déroulante de filtre, avec « Tous » en première option. */
export function FilterSelect({ label, value, allLabel, options, onChange }: FilterSelectProps) {
  return (
    <label className="flex min-w-40 flex-1 flex-col gap-1 text-sm font-medium">
      {label}
      <select
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value === "" ? null : event.target.value)}
        className={fieldClass}
      >
        <option value="">{allLabel}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
