import { focusManager } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { fetchRun } from "../api";
import type { RunProgress, RunStatus } from "../types";

/** Intervalle de relecture de la sortie (le contrat dit : toutes les 300 ms). */
export const POLL_MS = 300;
/** Échecs de lecture de suite avant d'abandonner la lecture. */
export const MAX_FAILURES = 5;

export interface PolledRun {
  runId: string;
  status: RunStatus;
  output: string;
  exitCode: number | null;
  durationMs: number | null;
  truncated: boolean;
  error: string | null;
}

const waiting = (runId: string): PolledRun => ({
  runId,
  status: "running",
  output: "",
  exitCode: null,
  durationMs: null,
  truncated: false,
  error: null,
});

function fromProgress(runId: string, output: string, p: RunProgress): PolledRun {
  return {
    runId,
    status: p.status,
    output,
    exitCode: p.exit_code,
    durationMs: p.duration_ms,
    truncated: p.truncated,
    error: null,
  };
}

/**
 * Lit la sortie de `runId` toutes les 300 ms **par décalage** (`after` = `next_offset` reçu), et
 * s'arrête dès que le bac à sable a rendu une fin ; `onFinished` part alors, une seule fois. Une
 * lecture qui échoue cinq fois de suite arrête la lecture avec un message. Sans `runId`, rien ne
 * tourne.
 */
export function useRunPolling(runId: string | null, onFinished: (run: RunProgress) => void) {
  const [state, setState] = useState<PolledRun | null>(null);
  const finished = useRef(onFinished);
  useEffect(() => {
    finished.current = onFinished;
  });
  useEffect(() => {
    if (!runId) return undefined;
    const control = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let offset = 0;
    let output = "";
    let failures = 0;
    const tick = async (): Promise<void> => {
      if (!focusManager.isFocused()) {
        timer = setTimeout(() => void tick(), POLL_MS); // onglet caché : on ne relit plus, on guette
        return;
      }
      try {
        const p = await fetchRun(runId, offset, control.signal);
        if (control.signal.aborted) return;
        offset = p.next_offset;
        output += p.output;
        failures = 0;
        setState(fromProgress(runId, output, p));
        if (p.status !== "running") return finished.current(p);
      } catch (failure) {
        if (control.signal.aborted) return;
        failures += 1;
        if (failures >= MAX_FAILURES) {
          const error = `${t("ide.output.pollFailed")} ${errorMessage(failure)}`;
          return setState({ ...waiting(runId), output, status: "error", error });
        }
      }
      timer = setTimeout(() => void tick(), POLL_MS);
    };
    void tick();
    return () => {
      control.abort();
      clearTimeout(timer);
    };
  }, [runId]);
  if (!runId) return null;
  return state?.runId === runId ? state : waiting(runId);
}
