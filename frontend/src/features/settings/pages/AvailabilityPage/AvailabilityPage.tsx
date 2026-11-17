import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useSettings } from "../../hooks/useSettings";
import { AvailabilityEditor } from "./AvailabilityEditor";

/** Réglages > Disponibilité et rythme : temps disponible, brief, relances, débats et langue. */
export function AvailabilityPage() {
  const settings = useSettings();
  if (settings.isError) {
    return (
      <ErrorState message={errorMessage(settings.error)} onRetry={() => void settings.refetch()} />
    );
  }
  if (!settings.data) return <LoadingState label={t("settings.availability.loading")} />;
  return <AvailabilityEditor settings={settings.data} />;
}
