import { useCallback, useMemo, useState } from "react";

export interface PollingBudget {
  /** Reads already done. */
  used: number;
  /** The allowed number of reads is reached: stop re-reading. */
  exhausted: boolean;
  /** Call on each read (in the query's read function). */
  spend: () => void;
  /** Starts over from zero (« Réessayer »). */
  restart: () => void;
}

/**
 * Cap on re-reads of a page waiting for background work (quiz being prepared,
 * summary being written): a periodic retry never runs forever.
 */
export function usePollingBudget(max: number): PollingBudget {
  const [used, setUsed] = useState(0);
  const spend = useCallback(() => setUsed((count) => count + 1), []);
  const restart = useCallback(() => setUsed(0), []);
  return useMemo(
    () => ({ used, exhausted: used >= max, spend, restart }),
    [used, max, spend, restart],
  );
}
