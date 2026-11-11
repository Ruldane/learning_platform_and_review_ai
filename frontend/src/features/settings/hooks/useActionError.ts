import { useCallback, useState } from "react";
import { errorMessage } from "@/shared/api/errors";

export type TrackAction = <T>(action: () => Promise<T>) => Promise<T>;

/**
 * Garde le dernier message d'erreur (français) des actions de l'écran. Lancer une nouvelle
 * action l'efface ; l'erreur est relancée pour que l'appelant sache que l'action a échoué.
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
