import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { AvailabilityDraft } from "../../availabilitySettings";
import { DelaysField } from "../../components/DelaysField";

interface BriefFieldsProps {
  draft: AvailabilityDraft;
  timeInvalid: boolean;
  timeRefused: boolean;
  delaysInvalid: boolean;
  delaysRefused: boolean;
  onChange: (next: AvailabilityDraft) => void;
}

/** Heure du brief du matin et délais des trois relances. */
export function BriefFields(props: BriefFieldsProps) {
  const { draft, timeInvalid, timeRefused, delaysInvalid, delaysRefused, onChange } = props;
  const hintId = useId();
  const bad = timeInvalid || timeRefused;
  const setDelay = (index: 0 | 1 | 2, text: string) => {
    const delays: [string, string, string] = [...draft.delays];
    delays[index] = text;
    onChange({ ...draft, delays });
  };
  return (
    <>
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium">
          {t("settings.availability.briefTime")}
          <input
            type="time"
            value={draft.briefTime}
            aria-invalid={bad}
            aria-describedby={hintId}
            onChange={(event) => onChange({ ...draft, briefTime: event.target.value })}
            className={`${fieldClass} mt-1 block w-32`}
          />
        </label>
        <p
          id={hintId}
          className={bad ? "text-sm text-destructive" : "text-sm text-muted-foreground"}
        >
          {timeRefused && !timeInvalid
            ? t("settings.fields.refused")
            : t("settings.availability.briefTimeHint")}
        </p>
      </div>
      <DelaysField
        value={draft.delays}
        invalid={delaysInvalid}
        refused={delaysRefused}
        onChange={setDelay}
      />
    </>
  );
}
