import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useInterview } from "../../hooks/useInterview";
import { applicationsKeys } from "../../queryKeys";
import { InterviewLive } from "./InterviewLive";
import { InterviewOutcome } from "./InterviewOutcome";

interface InterviewFollowProps {
  interviewId: string;
  /** Un entretien était déjà ouvert : on le reprend, et on le dit. */
  resumed: boolean;
  /** L'entretien vient d'être suivi en direct : le retour propose d'en commencer un autre. */
  live: boolean;
  createSocket?: SocketFactory;
  onClose: () => void;
}

/**
 * Un entretien suivi : tant qu'il tourne, son fil ; dès qu'il est fini, son débrief (ou ce qui manque).
 * La liste des entretiens est relue à chaque changement d'état, pour que la page ne revienne pas
 * sur un entretien déjà fini.
 */
export function InterviewFollow({
  interviewId,
  resumed,
  live,
  createSocket,
  onClose,
}: InterviewFollowProps) {
  const client = useQueryClient();
  const interview = useInterview(interviewId);
  const status = interview.data?.status;

  useEffect(() => {
    if (status && status !== "running") {
      void client.invalidateQueries({ queryKey: applicationsKeys.allInterviews });
    }
  }, [client, status]);

  if (interview.isPending) {
    return <LoadingState label={t("applications.interviewPage.loading")} />;
  }
  if (interview.isError) {
    return (
      <ErrorState
        message={errorMessage(interview.error)}
        onRetry={() => void interview.refetch()}
      />
    );
  }
  if (interview.data.status === "running") {
    return (
      <div className="flex flex-col gap-3">
        {resumed ? (
          <p role="status" className="text-sm">
            {t("applications.interviewPage.resumed")}
          </p>
        ) : null}
        <InterviewLive interview={interview.data} createSocket={createSocket} />
      </div>
    );
  }
  return (
    <InterviewOutcome
      interview={interview.data}
      closeLabel={t(
        live ? "applications.interviewPage.another" : "applications.interviewPage.backToSettings",
      )}
      onClose={onClose}
    />
  );
}
