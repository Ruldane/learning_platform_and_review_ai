import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useSessionActions } from "@/shared/realtime/useSessionActions";
import { useSessionStream } from "@/shared/realtime/useSessionStream";
import { studyKeys } from "../queryKeys";
import type { StudySessionOut } from "../types";
import { useFinishStudy } from "./useFinishStudy";

interface StudyRunOptions {
  session: StudySessionOut;
  /** « Terminer » was accepted: the Tutor concludes. */
  finishing: boolean;
  onFinishing: () => void;
  createSocket?: SocketFactory;
}

const OVER = ["completed", "failed", "cancelled", "expired"] as const;

/**
 * A study session under way: the Tutor's stream (only while the agent session is live), the
 * session actions over REST, the worked time (read on send, never copied on every second)
 * and « Terminer ». « Terminer » is possible only when the Tutor waits for an answer
 * (`waiting_user`, else 409) or its session has stopped (`interrupted`: the time is saved).
 */
export function useStudyRun({ session, finishing, onFinishing, createSocket }: StudyRunOptions) {
  const queryClient = useQueryClient();
  const live = session.status === "open" && session.session_id !== null;
  const stream = useSessionStream(live ? session.session_id : null, { createSocket });
  const actions = useSessionActions(session.session_id ?? "");
  const finisher = useFinishStudy(session.id);
  const worked = useRef(0);

  // The agent session has ended: the study session's state has changed (summary, stop).
  const over = live && (OVER as readonly string[]).includes(stream.status);
  useEffect(() => {
    if (over) void queryClient.invalidateQueries({ queryKey: studyKeys.session(session.id) });
  }, [over, queryClient, session.id]);

  const waiting = session.status === "interrupted" || (live && stream.status === "waiting_user");
  const canFinish = waiting && !finishing && !finisher.pending;
  const finish = async () => {
    if (await finisher.finish(worked.current)) onFinishing();
  };
  return {
    stream,
    actions,
    canFinish,
    finish,
    finishError: finisher.error,
    finishPending: finisher.pending,
    onWorkedChange: (seconds: number) => {
      worked.current = seconds;
    },
  };
}

export type StudyRun = ReturnType<typeof useStudyRun>;
