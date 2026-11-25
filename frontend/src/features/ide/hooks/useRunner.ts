import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { startRun } from "../api";
import type { OutputView } from "../components/viewTypes";
import { ideKeys } from "../queryKeys";
import { isFailedRun } from "../toView";
import type { Origin, RunKind, RunProgress } from "../types";
import { useClaudeRuns } from "./useClaudeRuns";
import { useLiveRuns } from "./useLiveRuns";
import { useRunPolling, type PolledRun } from "./useRunPolling";

const IDLE: OutputView = {
  runId: null,
  kind: null,
  origin: "app",
  status: "idle",
  output: "",
  exitCode: null,
  durationMs: null,
  truncated: false,
  error: null,
};

interface Watched {
  id: string;
  kind: RunKind;
  origin: Origin;
}

function toOutput(run: Watched, polled: PolledRun): OutputView {
  return {
    runId: polled.runId,
    kind: run.kind,
    origin: run.origin,
    status: polled.status,
    output: polled.output,
    exitCode: polled.exitCode,
    durationMs: polled.durationMs,
    truncated: polled.truncated,
    error: polled.error,
  };
}

/** The run read has ended in failure: its id, otherwise `null`. */
function failedRun(polled: PolledRun | null): string | null {
  if (polled === null || polled.status === "running") return null;
  return isFailedRun({ status: polled.status, exit_code: polled.exitCode }) ? polled.runId : null;
}

/**
 * Starts a run or a check: the code is saved first (`flush`), then the
 * output is read to the end. One run at a time; Ctrl+Enter during a run
 * does nothing. At the end, the session is re-read (a passing check sets it to « réussie »).
 * A run started by Claude (MCP) appears in the output on its own, marked « lancée par
 * Claude »; it never calls the teacher (`onFinished` only fires for yours).
 */
export function useRunner(
  sessionId: string,
  flush: () => Promise<boolean>,
  onFinished: (run: RunProgress) => void,
) {
  const queryClient = useQueryClient();
  const [run, setRun] = useState<Watched | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const busy = useRef(false);
  const polled = useRunPolling(run?.id ?? null, (finished) => {
    void queryClient.invalidateQueries({ queryKey: ideKeys.session(sessionId) });
    void queryClient.invalidateQueries({ queryKey: ideKeys.sessions });
    void queryClient.invalidateQueries({ queryKey: ideKeys.runs(sessionId) });
    if (run?.origin === "app") onFinished(finished);
  });
  useClaudeRuns(useLiveRuns(sessionId).data, run?.id ?? null, setRun);
  const start = useCallback(
    async (next: RunKind) => {
      if (busy.current) return;
      busy.current = true;
      setStarting(true);
      setError(null);
      try {
        if (!(await flush())) return setError(t("ide.toolbar.saveBeforeRun"));
        setRun({ id: (await startRun(sessionId, next)).id, kind: next, origin: "app" });
      } catch (failure) {
        setError(errorMessage(failure));
      } finally {
        busy.current = false;
        setStarting(false);
      }
    },
    [flush, sessionId],
  );
  const output = polled && run ? toOutput(run, polled) : IDLE;
  const failedRunId = failedRun(polled);
  const running = starting || polled?.status === "running";
  return {
    output,
    running,
    startError: error,
    failedRunId,
    lastRunId: polled?.runId ?? null,
    start,
  };
}
