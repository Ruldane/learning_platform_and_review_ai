import { t } from "@/shared/i18n/t";
import {
  BREAK_RANGE,
  WORK_RANGE,
  type StudyDraft,
  type StudyDraftErrors,
} from "../../studySettings";
import { DurationField } from "./DurationField";

interface RhythmFieldsProps {
  draft: StudyDraft;
  errors: StudyDraftErrors;
  onChange: (next: StudyDraft) => void;
}

/** Durées du minuteur : travail (10 à 120 minutes) et pause (0 à 60). */
export function RhythmFields({ draft, errors, onChange }: RhythmFieldsProps) {
  return (
    <div className="flex flex-wrap gap-6">
      <DurationField
        label={t("settings.study.work")}
        value={draft.work}
        range={WORK_RANGE}
        invalid={errors.work}
        onChange={(work) => onChange({ ...draft, work })}
      />
      <DurationField
        label={t("settings.study.pause")}
        value={draft.pause}
        range={BREAK_RANGE}
        invalid={errors.pause}
        onChange={(pause) => onChange({ ...draft, pause })}
      />
    </div>
  );
}
