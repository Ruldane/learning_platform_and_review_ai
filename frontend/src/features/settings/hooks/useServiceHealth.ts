import { useQuery } from "@tanstack/react-query";
import { fetchHealth } from "../api";
import { settingsKeys } from "../queryKeys";

export const SERVICE_HEALTH_MS = 5_000;

/**
 * L'état des services pour l'étape 1 du premier lancement, relu toutes les 5 s tant que l'étape
 * est affichée. Une lecture ratée ne casse rien : la suivante réessaie.
 */
export function useServiceHealth() {
  return useQuery({
    queryKey: settingsKeys.onboardingHealth,
    queryFn: ({ signal }) => fetchHealth(signal),
    refetchInterval: SERVICE_HEALTH_MS,
    retry: false,
  });
}
