import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useSettings } from "../../hooks/useSettings";
import { StudySettingsEditor } from "./StudySettingsEditor";

/** Réglages > Étude et bilan : durées du minuteur, jour et heure du bilan, fuseau horaire. */
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
