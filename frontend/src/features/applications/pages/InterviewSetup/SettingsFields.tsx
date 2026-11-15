import { t } from "@/shared/i18n/t";
import { OptionGroup } from "../../components/OptionGroup";
import { questionCount } from "../../toInterviewView";
import {
  INTERVIEW_DURATIONS,
  INTERVIEW_LANGUAGES,
  INTERVIEW_MODES,
  type InterviewDurationView,
  type InterviewLanguageView,
  type InterviewModeView,
} from "../../types";
import type { InterviewSettings } from "../../hooks/useStartInterview";

interface SettingsFieldsProps {
  settings: InterviewSettings;
  disabled: boolean;
  onChange: (settings: InterviewSettings) => void;
}

/** Les trois réglages d'un entretien : la formule, la durée (donc le nombre de questions) et la langue. */
export function SettingsFields({ settings, disabled, onChange }: SettingsFieldsProps) {
  return (
    <>
      <OptionGroup
        legend={t("applications.interviewSetup.mode.legend")}
        name="mode"
        value={settings.mode}
        disabled={disabled}
        options={INTERVIEW_MODES.map((mode) => ({
          value: mode,
          label: t(`applications.interviewSetup.mode.${mode}.label`),
          hint: t(`applications.interviewSetup.mode.${mode}.hint`),
        }))}
        onChange={(mode) => onChange({ ...settings, mode: mode as InterviewModeView })}
      />
      <OptionGroup
        legend={t("applications.interviewSetup.duration.legend")}
        name="duration"
        value={String(settings.durationMin)}
        disabled={disabled}
        options={INTERVIEW_DURATIONS.map((minutes) => ({
          value: String(minutes),
          label: t("applications.interviewSetup.duration.label", { minutes }),
          hint: t("applications.interviewSetup.duration.hint", { count: questionCount(minutes) }),
        }))}
        onChange={(value) =>
          onChange({ ...settings, durationMin: Number(value) as InterviewDurationView })
        }
      />
      <OptionGroup
        legend={t("applications.interviewSetup.language.legend")}
        name="language"
        value={settings.language}
        disabled={disabled}
        options={INTERVIEW_LANGUAGES.map((language) => ({
          value: language,
          label: t(`applications.interviewSetup.language.${language}`),
        }))}
        onChange={(language) =>
          onChange({ ...settings, language: language as InterviewLanguageView })
        }
      />
    </>
  );
}
