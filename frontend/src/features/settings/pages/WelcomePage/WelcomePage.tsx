import { useEffect, useRef } from "react";
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
 * « Tout supprimer » en mode local, `state.deleted` fait dire que les données sont parties : la
 * zone `status` est dans la page dès le premier rendu, vide, et le message y entre ensuite (une
 * zone insérée déjà remplie n'est pas annoncée de façon fiable) : son texte est posé par un
 * effet, sur le nœud, hors du rendu.
 */
export function WelcomePage() {
  const settings = useSettings();
  const deleted = (useLocation().state as { deleted?: boolean } | null)?.deleted === true;
  const notice = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    if (notice.current) notice.current.textContent = deleted ? t("onboarding.page.deleted") : "";
  }, [deleted]);
  return (
    <div className="flex flex-col gap-4">
      <p
        ref={notice}
        role="status"
        data-testid="welcome-notice"
        className="text-sm text-muted-foreground empty:sr-only"
      />
      {settings.data ? (
        <WelcomeSteps settings={settings.data} />
      ) : settings.isError ? (
        <ErrorState
          message={errorMessage(settings.error)}
          onRetry={() => void settings.refetch()}
        />
      ) : (
        <LoadingState label={t("onboarding.page.loading")} />
      )}
    </div>
  );
}
