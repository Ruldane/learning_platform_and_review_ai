import { useQuery } from "@tanstack/react-query";
import { fetchHealth } from "../api";
import { settingsKeys } from "../queryKeys";

export const SERVICE_HEALTH_MS = 5_000;

/**
 * The services' state for step 1 of the first run, reread every 5 s while the step
 * is shown. A failed read breaks nothing: the next one retries.
 */
export function useServiceHealth() {
  return useQuery({
    queryKey: settingsKeys.onboardingHealth,
    queryFn: ({ signal }) => fetchHealth(signal),
    refetchInterval: SERVICE_HEALTH_MS,
    retry: false,
  });
}
