import { useCallback, useEffect, useRef } from "react";
import type { RunSource } from "@/shared/lib/runSource";
import { isFailedRun } from "../toView";
import type { RunProgress, TeachIn } from "../types";
import { useTeach } from "./useTeach";

/** Where the learner is in the code: attached to each call so the teacher can place the help. */
export interface Where {
  filePath: string;
  line: number | null;
}

/** The fields of a call the caller picks; the location is added here. */
export type Ask = Pick<TeachIn, "trigger" | "question" | "run_id">;

/**
 * The actions that wake the teacher, and only those. `ask` is sent on an action (Indice,
 * Pourquoi, minuterie, question). `afterRun` is sent at the end of a **failed** run, once per
 * run, and only if automatic mode is on (`automatic`): cap
 * reached, « sur demande » mode, or settings not read yet, no call is sent on its own.
 */
export function useCoach(sessionId: string, automatic: boolean, where: Where) {
  const teach = useTeach(sessionId);
  const handled = useRef(new Set<string>());
  const latest = useRef({ automatic, where });
  useEffect(() => {
    latest.current = { automatic, where };
  });
  const { mutate, mutateAsync } = teach;
  const ask = useCallback(
    (what: Ask, source?: RunSource) => {
      const { filePath, line } = latest.current.where;
      mutate({ ...what, file_path: filePath, line, source });
    },
    [mutate],
  );
  /** A typed question: `true` if the teacher takes it (otherwise the input stays in place). */
  const sendQuestion = useCallback(
    async (question: string, runId: string | null, source?: RunSource): Promise<boolean> => {
      const { filePath, line } = latest.current.where;
      try {
        const out = await mutateAsync({
          trigger: "question",
          question,
          run_id: runId,
          file_path: filePath,
          line,
          source,
        });
        return !out.skipped;
      } catch {
        return false; // the error is read from `teach.error`
      }
    },
    [mutateAsync],
  );
  const afterRun = useCallback(
    (run: RunProgress) => {
      if (!isFailedRun(run) || !latest.current.automatic || handled.current.has(run.id)) return;
      handled.current.add(run.id);
      ask({ trigger: "run_error", run_id: run.id });
    },
    [ask],
  );
  return { teach, ask, sendQuestion, afterRun };
}
