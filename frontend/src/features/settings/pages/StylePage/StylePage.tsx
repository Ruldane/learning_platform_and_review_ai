import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useSettings } from "../../hooks/useSettings";
import { StyleEditor } from "./StyleEditor";

/** Réglages > Style : le guide de style personnel que lisent les agents qui rédigent. */
export function StylePage() {
  const settings = useSettings();
  if (settings.isError) {
    return (
      <ErrorState message={errorMessage(settings.error)} onRetry={() => void settings.refetch()} />
    );
  }
  if (!settings.data) return <LoadingState label={t("settings.style.loading")} />;
  return <StyleEditor settings={settings.data} />;
}
