import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { TaskType } from "../viewTypes";
import { TaskField } from "./TaskField";

const TYPES: TaskType[] = ["read", "watch", "practice", "quiz", "project"];

interface TypeFieldProps {
  value: TaskType;
  disabled: boolean;
  onChange: (type: TaskType) => void;
}

/** Choice of task type: read, watch, practise, quiz or project. */
export function TypeField({ value, disabled, onChange }: TypeFieldProps) {
  return (
    <TaskField label={t("program.add.type")} error={undefined}>
      {(aria) => (
        <select
          {...aria}
          value={value}
          disabled={disabled}
          className={fieldClass}
          onChange={(event) => onChange(event.target.value as TaskType)}
        >
          {TYPES.map((type) => (
            <option key={type} value={type}>
              {t(`program.taskType.${type}`)}
            </option>
          ))}
        </select>
      )}
    </TaskField>
  );
}
