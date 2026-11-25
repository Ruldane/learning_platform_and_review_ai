import { useQuery } from "@tanstack/react-query";
import { fetchSession } from "../api";
import { ideKeys } from "../queryKeys";
import { liveOptions } from "./live";

/** A session with its files (`GET /ide/sessions/{id}`), re-read live (Claude can write). */
export function useIdeSession(sessionId: string) {
  return useQuery({
    queryKey: ideKeys.session(sessionId),
    queryFn: ({ signal }) => fetchSession(sessionId, signal),
    ...liveOptions,
  });
}
