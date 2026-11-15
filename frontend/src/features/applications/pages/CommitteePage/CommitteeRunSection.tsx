import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import type { useCommittee } from "../../hooks/useCommittee";
import type { useCommittees } from "../../hooks/useCommittees";
import { CommitteeRun } from "./CommitteeRun";

interface CommitteeRunSectionProps {
  committees: ReturnType<typeof useCommittees>;
  run: ReturnType<typeof useCommittee>;
  /** L'exécution suivie, `null` quand l'offre n'en a pas encore. */
  runId: string | null;
  createSocket?: SocketFactory;
}

/** L'exécution suivie : chargement, panne, exécution disparue, absence d'exécution, ou le débat et les résultats. */
export function CommitteeRunSection({
  committees,
  run,
  runId,
  createSocket,
}: CommitteeRunSectionProps) {
  if (runId === null) {
    if (committees.isError) {
      return (
        <ErrorState
          message={errorMessage(committees.error)}
          onRetry={() => void committees.refetch()}
        />
      );
    }
    if (committees.isPending)
      return <LoadingState label={t("applications.committeePage.loading")} />;
    return (
      <p className="max-w-prose text-muted-foreground">{t("applications.committeePage.noRun")}</p>
    );
  }
  if (run.data)
    return <CommitteeRun key={run.data.id} view={run.data} createSocket={createSocket} />;
  if (run.error instanceof ApiError && run.error.status === 404) {
    return <p role="alert">{t("applications.committeePage.runMissing")}</p>;
  }
  if (run.isError) {
    return <ErrorState message={errorMessage(run.error)} onRetry={() => void run.refetch()} />;
  }
  return <LoadingState label={t("applications.committeePage.runLoading")} />;
}
