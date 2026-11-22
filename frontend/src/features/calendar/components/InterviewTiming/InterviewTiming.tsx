import { t } from "@/shared/i18n/t";
import { fieldClass } from "../formStyles";

export function InterviewTiming({ disabled }: { disabled: boolean }) {
  return (
    <>
      <label>
        {t("calendar.time")}
        <input name="time" className={fieldClass} type="time" required disabled={disabled} />
      </label>
      <label>
        {t("calendar.minutes")}
        <input
          name="minutes"
          className={fieldClass}
          type="number"
          min={15}
          max={180}
          defaultValue={45}
          required
          disabled={disabled}
        />
      </label>
    </>
  );
}
