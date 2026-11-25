import { useEffect, useRef } from "react";
import { useLocation } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useSettings } from "../../hooks/useSettings";
import { WelcomeSteps } from "./WelcomeSteps";

/**
 * `/welcome`: the first run in five steps (SPEC 15.5, 17.3), outside navigation. The
 * gate has already read the settings, so the page opens without waiting; if the read is missing,
 * it says so with « Réessayer » (the step title takes focus when the settings arrive). After
 * « Tout supprimer » in local mode, `state.deleted` makes it say the data has gone: the
 * `status` zone is on the page from the first render, empty, and the message enters it later (a
 * zone inserted already filled is not reliably announced): its text is set by an
 * effect, on the node, outside the render.
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
