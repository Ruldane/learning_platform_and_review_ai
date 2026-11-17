import { useLocation } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useSettings } from "../../hooks/useSettings";
import { WelcomeSteps } from "./WelcomeSteps";

/**
 * `/bienvenue` : le premier lancement en cinq étapes (SPEC 15.5, 17.3), hors de la navigation. La
 * porte a déjà lu les réglages, donc la page s'ouvre sans attendre ; si la lecture manque, elle le
 * dit avec « Réessayer » (le titre de l'étape prend le focus quand les réglages arrivent). Après
 * « Tout supprimer » en mode local, `state.deleted` fait dire que les données sont parties.
 */
export function WelcomePage() {
  const settings = useSettings();
  const deleted = (useLocation().state as { deleted?: boolean } | null)?.deleted === true;
  if (settings.data) {
    return (
      <>
        {deleted ? (
          <p role="status" className="mb-4 text-sm text-muted-foreground">
            {t("onboarding.page.deleted")}
          </p>
        ) : null}
        <WelcomeSteps settings={settings.data} />
      </>
    );
  }
  if (settings.isError) {
    return (
      <ErrorState message={errorMessage(settings.error)} onRetry={() => void settings.refetch()} />
    );
  }
  return <LoadingState label={t("onboarding.page.loading")} />;
}
