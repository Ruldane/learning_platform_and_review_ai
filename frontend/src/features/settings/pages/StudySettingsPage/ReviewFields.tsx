import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import {
  WEEKDAYS,
  type StudyDraft,
  type StudyDraftErrors,
  type Weekday,
} from "../../studySettings";
import { ZoneField } from "./ZoneField";

interface ReviewFieldsProps {
  draft: StudyDraft;
  errors: StudyDraftErrors;
  onChange: (next: StudyDraft) => void;
}

/** Jour et heure du bilan de la semaine, puis le fuseau horaire. */
export function ReviewFields({ draft, errors, onChange }: ReviewFieldsProps) {
  const timeHint = useId();
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-6">
        <label className="text-sm font-medium">
          {t("settings.study.day")}
          <select
            value={draft.day}
            onChange={(event) => onChange({ ...draft, day: event.target.value as Weekday })}
            className={`${fieldClass} mt-1 w-44`}
          >
            {WEEKDAYS.map((day) => (
              <option key={day} value={day}>
                {t(`settings.study.days.${day}`)}
              </option>
            ))}
          </select>
        </label>
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium">
            {t("settings.study.time")}
            <input
              type="time"
              value={draft.time}
              aria-invalid={errors.time}
              aria-describedby={timeHint}
              onChange={(event) => onChange({ ...draft, time: event.target.value })}
              className={`${fieldClass} mt-1 w-32`}
            />
          </label>
          <p
            id={timeHint}
            className={errors.time ? "text-sm text-destructive" : "text-sm text-muted-foreground"}
          >
            {t("settings.study.timeHint")}
          </p>
        </div>
      </div>
      <ZoneField value={draft.zone} onChange={(zone) => onChange({ ...draft, zone })} />
    </div>
  );
}
