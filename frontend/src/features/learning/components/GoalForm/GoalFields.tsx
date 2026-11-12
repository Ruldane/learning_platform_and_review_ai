import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { fieldClass } from "@/shared/ui/fieldClass";
import { GoalField } from "./GoalField";
import { GoalMetaFields } from "./GoalMetaFields";
import type { GoalDraft, GoalErrors } from "./parseGoal";

interface GoalFieldsProps {
  draft: GoalDraft;
  errors: GoalErrors;
  disabled: boolean;
  onChange: (field: keyof GoalDraft, value: string) => void;
}

/** Les quatre champs d'un objectif : texte, poste visé, échéance, heures par semaine. */
export function GoalFields({ draft, errors, disabled, onChange }: GoalFieldsProps) {
  return (
    <>
      <GoalField
        label={t("learning.goals.form.text")}
        hint={t("learning.goals.form.textHint")}
        error={errors.text}
      >
        {(props) => (
          <textarea
            {...props}
            rows={3}
            value={draft.text}
            disabled={disabled}
            onChange={(event) => onChange("text", event.target.value)}
            className={cn(fieldClass, "h-auto resize-y py-1.5")}
          />
        )}
      </GoalField>
      <GoalMetaFields draft={draft} errors={errors} disabled={disabled} onChange={onChange} />
    </>
  );
}
