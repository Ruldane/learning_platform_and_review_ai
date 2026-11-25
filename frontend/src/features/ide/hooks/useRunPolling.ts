import { focusManager } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { fetchRun } from "../api";
import type { RunProgress, RunStatus } from "../types";

/** Output re-read interval (the contract says: every 300 ms). */
export const POLL_MS = 300;
/** Consecutive read failures before giving up reading. */
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
 * Reads the output of `runId` every 300 ms **by offset** (`after` = `next_offset` received), and
 * stops as soon as the sandbox reports an end; `onFinished` then fires, once. A
 * read that fails five times in a row stops reading with a message. Without `runId`, nothing
 * tourne.
 */
export function useRunPolling(
  runId: string | null,
  onFinished: (run: RunProgress) => void,
  read = fetchRun,
) {
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
        timer = setTimeout(() => void tick(), POLL_MS); // hidden tab: no re-reads until it returns
        return;
      }
      try {
        const p = await read(runId, offset, control.signal);
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
  }, [read, runId]);
  if (!runId) return null;
  return state?.runId === runId ? state : waiting(runId);
}
