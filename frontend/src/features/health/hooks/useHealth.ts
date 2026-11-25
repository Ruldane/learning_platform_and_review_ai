import { useQuery } from "@tanstack/react-query";
import { fetchHealth } from "../api";

export const HEALTH_REFETCH_MS = 30_000;

/** Service status, refreshed every 30 s (the request is cancelled if the component unmounts). */
export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => fetchHealth(signal),
    refetchInterval: HEALTH_REFETCH_MS,
    // An unreachable server must show at once; the next round retries.
    retry: false,
  });
}
