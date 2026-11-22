import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { ReviewPreferences } from "../../api";

export function WindowFields({
  draft,
  timezone,
  onChange,
}: {
  draft: ReviewPreferences;
  timezone: string;
  onChange: (patch: Partial<ReviewPreferences>) => void;
}) {
  return (
    <>
      <p>{t("messageReview.timezone", { timezone })}</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="grid gap-1">
          {t("messageReview.start")}
          <input
            className={fieldClass}
            type="time"
            required
            value={draft.start}
            onChange={(e) => onChange({ start: e.target.value })}
          />
        </label>
        <label className="grid gap-1">
          {t("messageReview.end")}
          <input
            className={fieldClass}
            type="time"
            required
            value={draft.end}
            onChange={(e) => onChange({ end: e.target.value })}
          />
        </label>
      </div>
    </>
  );
}
