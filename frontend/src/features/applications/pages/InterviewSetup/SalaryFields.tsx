import { t } from "@/shared/i18n/t";
import { fieldClass } from "@/shared/ui/fieldClass";
import type { InterviewSettings } from "../../hooks/useStartInterview";

interface SalaryFieldsProps {
  settings: InterviewSettings;
  disabled: boolean;
  onChange: (settings: InterviewSettings) => void;
}

export function SalaryFields({ settings, disabled, onChange }: SalaryFieldsProps) {
  return (
    <fieldset disabled={disabled} className="grid gap-2 sm:grid-cols-2">
      <legend className="mb-2 text-sm font-semibold">
        {t("applications.interviewSetup.salarySource.legend")}
      </legend>
      <label className="grid gap-1 text-sm">
        {t("applications.interviewSetup.salarySource.role")}
        <input
          value={settings.radarRole ?? ""}
          maxLength={120}
          className={fieldClass}
          onChange={(event) => onChange({ ...settings, radarRole: event.currentTarget.value })}
        />
      </label>
      <label className="grid gap-1 text-sm">
        {t("applications.interviewSetup.salarySource.zone")}
        <input
          value={settings.radarZone ?? ""}
          maxLength={120}
          className={fieldClass}
          onChange={(event) => onChange({ ...settings, radarZone: event.currentTarget.value })}
        />
      </label>
      <p className="text-sm text-muted-foreground sm:col-span-2">
        {t("applications.interviewSetup.salarySource.hint")}
      </p>
    </fieldset>
  );
}
