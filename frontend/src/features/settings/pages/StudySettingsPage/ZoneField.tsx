import { useId, useMemo } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import { timezoneChoices } from "../../studySettings";

interface ZoneFieldProps {
  value: string;
  onChange: (zone: string) => void;
}

/** Le fuseau horaire : la liste des fuseaux IANA que connaît le navigateur. */
export function ZoneField({ value, onChange }: ZoneFieldProps) {
  const hintId = useId();
  const zones = useMemo(() => timezoneChoices(value), [value]);
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium">
        {t("settings.study.zone")}
        <select
          value={value}
          aria-describedby={hintId}
          onChange={(event) => onChange(event.target.value)}
          className={`${fieldClass} mt-1 max-w-sm`}
        >
          {zones.map((zone) => (
            <option key={zone} value={zone}>
              {zone}
            </option>
          ))}
        </select>
      </label>
      <p id={hintId} className="text-sm text-muted-foreground">
        {t("settings.study.zoneHint")}
      </p>
    </div>
  );
}
