import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useSettings } from "../../hooks/useSettings";
import { StudySettingsEditor } from "./StudySettingsEditor";

/** Settings > Study and review: timer durations, review day and time, time zone. */
export function StudySettingsPage() {
  const settings = useSettings();
  if (settings.isError) {
    return (
      <ErrorState message={errorMessage(settings.error)} onRetry={() => void settings.refetch()} />
    );
  }
  if (!settings.data) return <LoadingState label={t("settings.study.loading")} />;
  return <StudySettingsEditor settings={settings.data} />;
}
