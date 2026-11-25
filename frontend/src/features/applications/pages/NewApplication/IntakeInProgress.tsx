import { t } from "@/shared/i18n/t";
import { useSessionActions } from "@/shared/realtime/useSessionActions";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";

interface IntakeInProgressProps {
  sessionId: string;
  onResume: () => void;
  /** The open session is cancelled: another one can be started. */
  onCancelled: () => void;
}

/** A one-sentence entry is already open (409): resume it, or cancel it to start a new one. */
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
