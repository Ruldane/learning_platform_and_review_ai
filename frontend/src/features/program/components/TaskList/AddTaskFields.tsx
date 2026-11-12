import { t } from "@/shared/i18n/t";
import type { WeekView } from "../viewTypes";
import { DayField } from "./DayField";
import type { TaskDraft, TaskErrors } from "./parseTask";
import { TaskTextField } from "./TaskTextField";
import { TypeField } from "./TypeField";

interface AddTaskFieldsProps {
  draft: TaskDraft;
  errors: TaskErrors;
  weeks: WeekView[];
  disabled: boolean;
  onChange: (patch: Partial<TaskDraft>) => void;
}

/** Les cinq champs du formulaire d'ajout : titre, type, durée, jour et critère de fin. */
export function AddTaskFields({ draft, errors, weeks, disabled, onChange }: AddTaskFieldsProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <TaskTextField
        label={t("program.add.title")}
        hint={t("program.add.titleHint")}
        error={errors.title}
        value={draft.title}
        disabled={disabled}
        onChange={(title) => onChange({ title })}
      />
      <TypeField value={draft.type} disabled={disabled} onChange={(type) => onChange({ type })} />
      <TaskTextField
        label={t("program.add.minutes")}
        hint={t("program.add.minutesHint")}
        error={errors.minutes}
        value={draft.minutes}
        disabled={disabled}
        inputMode="numeric"
        onChange={(minutes) => onChange({ minutes })}
      />
      <DayField
        weeks={weeks}
        value={draft.plannedDate}
        error={errors.plannedDate}
        disabled={disabled}
        onChange={(plannedDate) => onChange({ plannedDate })}
      />
      <div className="sm:col-span-2">
        <TaskTextField
          label={t("program.add.criterion")}
          error={errors.doneCriterion}
          value={draft.doneCriterion}
          disabled={disabled}
          onChange={(doneCriterion) => onChange({ doneCriterion })}
        />
      </div>
    </div>
  );
}
