import { useQuery } from "@tanstack/react-query";
import { fetchRuns } from "../api";
import { ideKeys } from "../queryKeys";
import { liveOptions } from "./live";

/** The session's latest runs, re-read live (those started by Claude included). */
export function useLiveRuns(sessionId: string) {
  return useQuery({
    queryKey: ideKeys.runs(sessionId),
    queryFn: ({ signal }) => fetchRuns(sessionId, signal),
    ...liveOptions,
  });
}
