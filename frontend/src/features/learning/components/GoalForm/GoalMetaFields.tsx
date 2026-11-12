import { t } from "@/shared/i18n/t";
import { GoalInputField } from "./GoalInputField";
import { ROLE_MAX, todayIso, type GoalDraft, type GoalErrors } from "./parseGoal";

interface GoalMetaFieldsProps {
  draft: GoalDraft;
  errors: GoalErrors;
  disabled: boolean;
  onChange: (field: keyof GoalDraft, value: string) => void;
}

/** Poste visé, échéance et heures par semaine : les champs facultatifs d'un objectif. */
export function GoalMetaFields({ draft, errors, disabled, onChange }: GoalMetaFieldsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <GoalInputField
        label={t("learning.goals.form.targetRole")}
        hint={t("learning.goals.form.targetRoleHint")}
        error={errors.targetRole}
        value={draft.targetRole}
        disabled={disabled}
        onChange={(value) => onChange("targetRole", value)}
        input={{ type: "text", maxLength: ROLE_MAX * 2 }}
      />
      <GoalInputField
        label={t("learning.goals.form.deadline")}
        hint={t("learning.goals.form.deadlineHint")}
        error={errors.deadline}
        value={draft.deadline}
        disabled={disabled}
        onChange={(value) => onChange("deadline", value)}
        input={{ type: "date", min: todayIso() }}
      />
      <GoalInputField
        label={t("learning.goals.form.weeklyHours")}
        hint={t("learning.goals.form.weeklyHoursHint")}
        error={errors.weeklyHours}
        value={draft.weeklyHours}
        disabled={disabled}
        onChange={(value) => onChange("weeklyHours", value)}
        input={{ type: "text", inputMode: "numeric" }}
      />
    </div>
  );
}
