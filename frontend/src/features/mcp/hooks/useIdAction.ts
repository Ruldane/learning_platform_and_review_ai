import { useCallback, useRef, useState } from "react";
import { errorMessage } from "@/shared/api/errors";

/**
 * Runs an action on an item (token, request, change), refusing to run it twice
 * before the answer: a double click sends only one request, even before the next render. Keeps
 * the items in progress (`busyIds`) and the last error message, in French. `run` returns true if
 * the action succeeded.
 */
export function useIdAction<Args extends unknown[]>(
  action: (id: string, ...args: Args) => Promise<unknown>,
) {
  const inFlight = useRef(new Set<string>());
  const [busyIds, setBusyIds] = useState<readonly string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const run = useCallback(
    async (id: string, ...args: Args): Promise<boolean> => {
      if (inFlight.current.has(id)) return false;
      inFlight.current.add(id);
      setBusyIds([...inFlight.current]);
      setError(null);
      try {
        await action(id, ...args);
        return true;
      } catch (failure) {
        setError(errorMessage(failure));
        return false;
      } finally {
        inFlight.current.delete(id);
        setBusyIds([...inFlight.current]);
      }
    },
    [action],
  );
  return { run, busyIds, error };
}
