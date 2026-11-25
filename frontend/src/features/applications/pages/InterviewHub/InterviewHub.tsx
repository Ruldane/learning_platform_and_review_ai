import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useInterviews } from "../../hooks/useInterviews";
import { usePostingChoices } from "../../hooks/usePostingChoices";
import { InterviewSetup } from "../InterviewSetup";
import { InterviewFollow } from "./InterviewFollow";
import { PastInterviews } from "./PastInterviews";

interface InterviewHubProps {
  /** The record whose interviews are shown; `null`: the interviews without a record. */
  applicationId: string | null;
  createSocket?: SocketFactory;
}

interface Followed {
  id: string;
  resumed: boolean;
  /** Followed since its start (and not opened from the past interviews list). */
  live: boolean;
}

/**
 * The interview page content: the interview in progress (followed, or resumed on arrival),
 * otherwise the
 * settings to start one and the list of past interviews, whose debrief opens.
 */
export function InterviewHub({ applicationId, createSocket }: InterviewHubProps) {
  const list = useInterviews(applicationId);
  const [followed, setFollowed] = useState<Followed | null>(null);
  // The closed interviews: a finished interview is not resumed while the list says « en cours ».
  const [closed, setClosed] = useState<string[]>([]);
  const postings = usePostingChoices(applicationId === null).data;

  if (list.isPending) return <LoadingState label={t("applications.interviewPage.loading")} />;
  if (list.isError) {
    return <ErrorState message={errorMessage(list.error)} onRetry={() => void list.refetch()} />;
  }
  const running = list.data.find((interview) => interview.status === "running");
  // The interview in progress found on arrival is followed for good: its end does not make it
  // disappear.
  if (!followed && running && !closed.includes(running.id)) {
    setFollowed({ id: running.id, resumed: false, live: true });
  }
  const current = followed;
  if (current) {
    return (
      <InterviewFollow
        key={current.id}
        interviewId={current.id}
        resumed={current.resumed}
        live={current.live}
        createSocket={createSocket}
        applicationId={applicationId}
        onClose={() => {
          setClosed([...closed, current.id]);
          setFollowed(null);
        }}
      />
    );
  }
  return (
    <div className="flex flex-col gap-6">
      <InterviewSetup
        applicationId={applicationId}
        onStarted={(id, resumed) => setFollowed({ id, resumed, live: true })}
      />
      <PastInterviews
        interviews={list.data}
        postings={postings ?? []}
        onOpen={(id) => setFollowed({ id, resumed: false, live: false })}
      />
    </div>
  );
}
