import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { Level } from "../viewTypes";

const LEVELS: readonly Level[] = ["beginner", "intermediate", "advanced"];

interface GenerateLevelFieldProps {
  level: Level;
  onChange: (level: Level) => void;
}

export function GenerateLevelField({ level, onChange }: GenerateLevelFieldProps) {
  const id = useId();
  return (
    <>
      <label htmlFor={id} className="text-sm font-medium">
        {t("ide.form.level")}
      </label>
      <select
        id={id}
        value={level}
        onChange={(event) => onChange(event.target.value as Level)}
        className={fieldClass}
      >
        {LEVELS.map((value) => (
          <option key={value} value={value}>
            {t(`ide.form.levels.${value}`)}
          </option>
        ))}
      </select>
    </>
  );
}
