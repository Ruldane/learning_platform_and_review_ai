import { useQuery } from "@tanstack/react-query";
import { fetchRuns } from "../api";
import { ideKeys } from "../queryKeys";
import { liveOptions } from "./live";

/** Les dernières exécutions de la séance, relues en direct (celles lancées par Claude y passent). */
export function useLiveRuns(sessionId: string) {
  return useQuery({
    queryKey: ideKeys.runs(sessionId),
    queryFn: ({ signal }) => fetchRuns(sessionId, signal),
    ...liveOptions,
  });
}
