import { useCallback, useState } from "react";
import { errorMessage } from "@/shared/api/errors";

export type TrackAction = <T>(action: () => Promise<T>) => Promise<T>;

/**
 * Keeps the last error message (French) of the screen's actions. Starting a new
 * action clears it; the error is rethrown so the caller knows the action failed.
 */
export function useActionError() {
  const [error, setError] = useState<string | null>(null);
  const track = useCallback<TrackAction>(async (action) => {
    setError(null);
    try {
      return await action();
    } catch (failure) {
      setError(errorMessage(failure));
      throw failure;
    }
  }, []);
  return { error, track };
}
