import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { startRun } from "../api";
import type { OutputView } from "../components/viewTypes";
import { ideKeys } from "../queryKeys";
import { isFailedRun } from "../toView";
import type { RunKind, RunProgress } from "../types";
import { useRunPolling, type PolledRun } from "./useRunPolling";

const IDLE: OutputView = {
  runId: null,
  kind: null,
  status: "idle",
  output: "",
  exitCode: null,
  durationMs: null,
  truncated: false,
  error: null,
};

function toOutput(kind: RunKind, polled: PolledRun): OutputView {
  return {
    runId: polled.runId,
    kind,
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
 */
export function useRunner(
  sessionId: string,
  flush: () => Promise<boolean>,
  onFinished: (run: RunProgress) => void,
) {
  const queryClient = useQueryClient();
  const [run, setRun] = useState<{ id: string; kind: RunKind } | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const busy = useRef(false);
  const polled = useRunPolling(run?.id ?? null, (finished) => {
    void queryClient.invalidateQueries({ queryKey: ideKeys.session(sessionId) });
    void queryClient.invalidateQueries({ queryKey: ideKeys.sessions });
    onFinished(finished);
  });
  const start = useCallback(
    async (next: RunKind) => {
      if (busy.current) return;
      busy.current = true;
      setStarting(true);
      setError(null);
      try {
        if (!(await flush())) return setError(t("ide.toolbar.saveBeforeRun"));
        setRun({ id: (await startRun(sessionId, next)).id, kind: next });
      } catch (failure) {
        setError(errorMessage(failure));
      } finally {
        busy.current = false;
        setStarting(false);
      }
    },
    [flush, sessionId],
  );
  const output = polled && run ? toOutput(run.kind, polled) : IDLE;
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
