import { useQuery } from "@tanstack/react-query";
import { fetchRunningLearnings } from "../api";
import { memoryKeys } from "../queryKeys";

/**
 * Archivist sessions still running (`GET /sessions`, filtered), read once when the
 * Documents screen mounts, to resume tracking after a reload. No periodic polling:
 * each session's stream takes over.
 */
export function useRunningLearnings() {
  return useQuery({
    queryKey: memoryKeys.runningLearnings,
    queryFn: ({ signal }) => fetchRunningLearnings(signal),
    refetchOnWindowFocus: false,
  });
}
