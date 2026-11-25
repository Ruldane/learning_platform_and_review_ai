import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useInterview } from "../../hooks/useInterview";
import { applicationsKeys } from "../../queryKeys";
import { ResumedNote } from "./ResumedNote";
import { InterviewLive } from "./InterviewLive";
import { InterviewOutcome } from "./InterviewOutcome";

interface InterviewFollowProps {
  interviewId: string;
  /** An interview was already open: it is resumed, and this is said. */
  resumed: boolean;
  /** The interview was just followed live: the return offers to start another. */
  live: boolean;
  /** The record of the page; `null`: the free page. */
  applicationId: string | null;
  createSocket?: SocketFactory;
  onClose: () => void;
}

/**
 * A followed interview: while it runs, its thread; once finished, its debrief (or what is missing).
 * The interview list is re-read on each state change, so the page does not go back
 * to an interview already finished.
 */
export function InterviewFollow({
  interviewId,
  resumed,
  live,
  applicationId,
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
        {resumed ? <ResumedNote interview={interview.data} applicationId={applicationId} /> : null}
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
