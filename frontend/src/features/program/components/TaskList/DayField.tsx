import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import { longDay } from "@/shared/lib/format";
import type { WeekView } from "../viewTypes";
import { TaskField } from "./TaskField";

interface DayFieldProps {
  weeks: WeekView[];
  value: string;
  error: string | undefined;
  disabled: boolean;
  onChange: (date: string) => void;
}

/** Choix du jour de la tâche : les jours de chaque semaine, regroupés par semaine. */
export function DayField({ weeks, value, error, disabled, onChange }: DayFieldProps) {
  return (
    <TaskField label={t("program.add.day")} error={error}>
      {(aria) => (
        <select
          {...aria}
          value={value}
          disabled={disabled}
          className={fieldClass}
          onChange={(event) => onChange(event.target.value)}
        >
          <option value="">{t("program.add.dayPlaceholder")}</option>
          {weeks.map((week) => (
            <optgroup
              key={week.rank}
              label={t("program.add.weekGroup", { rank: week.rank, theme: week.theme })}
            >
              {week.days.map((day) => (
                <option key={day.date} value={day.date}>
                  {longDay(day.date)}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      )}
    </TaskField>
  );
}
