import { useEffect, useRef } from "react";
import type { RunStarted } from "../types";

/**
 * Shows in the output the run that Claude (MCP) just started: the newest of the list
 * re-read live, origin `mcp`, that has not been seen yet. On the first read, runs
 * already finished are known (an old result is not shown on open); a run still
 * in progress is followed. Never touches focus or the teacher.
 */
export function useClaudeRuns(
  runs: RunStarted[] | undefined,
  currentId: string | null,
  watch: (run: { id: string; kind: RunStarted["kind"]; origin: "mcp" }) => void,
) {
  const known = useRef<Set<string> | null>(null);
  useEffect(() => {
    if (!runs) return;
    if (known.current === null) {
      known.current = new Set(runs.filter((run) => run.status !== "running").map((run) => run.id));
    }
    const newest = runs[0];
    if (!newest || newest.origin !== "mcp") return;
    if (known.current.has(newest.id) || newest.id === currentId) return;
    known.current.add(newest.id);
    watch({ id: newest.id, kind: newest.kind, origin: "mcp" });
  }, [runs, currentId, watch]);
}
