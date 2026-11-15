import { t } from "@/shared/i18n/t";
import { useSessionActions } from "@/shared/realtime/useSessionActions";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";

interface IntakeInProgressProps {
  sessionId: string;
  onResume: () => void;
  /** La session ouverte est annulée : on peut en commencer une autre. */
  onCancelled: () => void;
}

/** Une saisie en une phrase est déjà ouverte (409) : la reprendre, ou l'annuler pour en refaire une. */
export function IntakeInProgress({ sessionId, onResume, onCancelled }: IntakeInProgressProps) {
  const actions = useSessionActions(sessionId);

  async function cancel() {
    if (await actions.cancel()) onCancelled();
  }

  return (
    <div role="alert" className="flex flex-col gap-3 rounded-xl border bg-card p-4 text-sm">
      <p>{t("applications.newPage.inProgress")}</p>
      {actions.error ? <InlineError message={actions.error} /> : null}
      <div className="flex flex-wrap gap-2">
        <Button type="button" onClick={onResume}>
          {t("applications.newPage.resume")}
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={actions.pending}
          onClick={() => void cancel()}
        >
          {t("applications.newPage.cancelSession")}
        </Button>
      </div>
    </div>
  );
}
