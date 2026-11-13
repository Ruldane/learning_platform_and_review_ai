import { useCallback, useMemo, useState } from "react";

export interface PollingBudget {
  /** Lectures déjà faites. */
  used: number;
  /** Le nombre de lectures permis est atteint : on arrête de relire. */
  exhausted: boolean;
  /** À appeler à chaque lecture (dans la fonction de lecture de la requête). */
  spend: () => void;
  /** Repart de zéro (« Réessayer »). */
  restart: () => void;
}

/**
 * Plafond des relectures d'une page qui attend un travail en tâche de fond (quiz en préparation,
 * bilan en rédaction) : une relance périodique ne tourne jamais sans fin.
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
