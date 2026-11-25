import { useEffect } from "react";
import type { StartedRun } from "../../hooks/useStartRadar";

/**
 * Launches whose focus is already set (by object: a new launch is a new
 * object).
 */
const spent = new WeakSet<StartedRun>();

/**
 * The focus that this page's launch gives the followed sweep's title: it is used only once.
 * `starter.started` stays in memory while the page is mounted; otherwise a detour to another
 * sweep in the history, then back to this one (still running), would take focus again although
 * no launch happened. The launch is marked consumed in an effect of the parent, which runs after
 * the title's (it takes focus on mount), so the next render does not ask again.
 * No state: nothing more renders.
 */
export function useLaunchFocus(started: StartedRun | null, runId: string | null, running: boolean) {
  const wanted = started !== null && started.runId === runId && !spent.has(started);
  useEffect(() => {
    if (wanted && running) spent.add(started);
  }, [wanted, running, started]);
  return wanted;
}
