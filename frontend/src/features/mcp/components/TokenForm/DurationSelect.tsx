import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import { EXPIRY_CHOICES, type ExpiryDays } from "../viewTypes";

interface DurationSelectProps {
  value: ExpiryDays;
  onChange: (days: ExpiryDays) => void;
}

/** The token lifetime: 1, 7, 30 or 90 days (native list). */
export function DurationSelect({ value, onChange }: DurationSelectProps) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {t("mcp.form.duration")}
      </label>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(Number(event.target.value) as ExpiryDays)}
        className={`${fieldClass} w-auto self-start`}
      >
        {EXPIRY_CHOICES.map((choice) => (
          <option key={choice} value={choice}>
            {t(`mcp.form.days.d${choice}`)}
          </option>
        ))}
      </select>
    </div>
  );
}
