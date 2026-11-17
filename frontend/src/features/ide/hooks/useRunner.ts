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

/** L'exécution lue est finie en échec : son identifiant, sinon `null`. */
function failedRun(polled: PolledRun | null): string | null {
  if (polled === null || polled.status === "running") return null;
  return isFailedRun({ status: polled.status, exit_code: polled.exitCode }) ? polled.runId : null;
}

/**
 * Lance une exécution ou une vérification : le code est d'abord enregistré (`flush`), puis la
 * sortie est lue jusqu'à la fin. Une seule exécution à la fois ; Ctrl+Entrée pendant une exécution
 * ne fait rien. À la fin, la séance est relue (une vérification réussie la passe en « réussie »).
 * Une exécution lancée par Claude (MCP) apparaît d'elle-même dans la sortie, marquée « lancée par
 * Claude » ; elle n'appelle jamais le professeur (`onFinished` ne part que pour les tiennes).
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
