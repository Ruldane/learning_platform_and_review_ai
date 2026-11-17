import { useCallback, useRef, useState } from "react";
import { errorMessage } from "@/shared/api/errors";

/**
 * Lance une action sur un élément (jeton, demande, changement) en refusant de la lancer deux fois
 * avant la réponse : un double clic n'envoie qu'une requête, même avant le prochain rendu. Garde
 * les éléments en cours (`busyIds`) et le dernier message d'erreur, en français. `run` rend vrai si
 * l'action a réussi.
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
