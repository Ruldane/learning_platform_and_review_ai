import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useSettings } from "../../hooks/useSettings";
import { WelcomeSteps } from "./WelcomeSteps";

/**
 * `/bienvenue` : le premier lancement en cinq étapes (SPEC 15.5, 17.3), hors de la navigation. La
 * porte a déjà lu les réglages, donc la page s'ouvre sans attendre ; si la lecture manque, elle le
 * dit avec « Réessayer » (le titre de l'étape prend le focus quand les réglages arrivent).
 */
export function WelcomePage() {
  const settings = useSettings();
  if (settings.data) return <WelcomeSteps settings={settings.data} />;
  if (settings.isError) {
    return (
      <ErrorState message={errorMessage(settings.error)} onRetry={() => void settings.refetch()} />
    );
  }
  return <LoadingState label={t("onboarding.page.loading")} />;
}
