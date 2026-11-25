import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useRun } from "@/shared/realtime/useRun";
import { RunFeed } from "@/shared/session-ui";
import { InlineError } from "@/shared/ui/states/InlineError";
import { SalaryScenario } from "../../components/SalaryScenario";
import { applicationsKeys } from "../../queryKeys";
import type { InterviewView } from "../../types";
import { announcementOf, isFinishing } from "./questionPosition";
import { renderQuestion } from "./renderQuestion";

interface InterviewLiveProps {
  interview: InterviewView;
  createSocket?: SocketFactory;
}

/**
 * The interview in progress: the interviewer's session thread, one question at a time, each
 * with its answer field. The thread only says when to re-read the interview (each state change
 * or new question): results always come from the read. A live region
 * announces each question (its rank and text).
 */
export function InterviewLive({ interview, createSocket }: InterviewLiveProps) {
  const client = useQueryClient();
  const sync = useCallback(
    () => void client.invalidateQueries({ queryKey: applicationsKeys.interview(interview.id) }),
    [client, interview.id],
  );
  const [stopped, setStopped] = useState(false);
  const run = useRun(interview.sessionId, sync, createSocket);
  const { feed, pendingInterrupt, error } = run.stream.view;
  const finishing =
    !run.over && isFinishing(feed, pendingInterrupt, interview.questionCount, stopped);
  const announcement = announcementOf(feed, pendingInterrupt, interview.questionCount);

  return (
    <div className="flex flex-col gap-3">
      <p role="status" className="sr-only">
        <span key={pendingInterrupt?.interrupt_id ?? "none"}>{announcement}</span>
      </p>
      {interview.salary ? <SalaryScenario data={interview.salary} /> : null}
      <RunFeed
        run={run}
        label={t("applications.interviewRun.feed")}
        renderInterrupt={(item) =>
          renderQuestion(item, run, interview.questionCount, () => setStopped(true))
        }
      />
      {finishing ? (
        <p role="status" className="text-sm font-medium">
          {t("applications.interviewRun.writing")}
        </p>
      ) : null}
      {run.over ? (
        <p role="status" className="text-sm font-medium">
          {t("applications.interviewRun.ending")}
        </p>
      ) : null}
      {error ? <InlineError message={error.message} /> : null}
    </div>
  );
}
