import { useQuery } from "@tanstack/react-query";
import { fetchSession } from "../api";
import { ideKeys } from "../queryKeys";
import { liveOptions } from "./live";

/** Une séance avec ses fichiers (`GET /ide/sessions/{id}`), relue en direct (Claude peut écrire). */
export function useIdeSession(sessionId: string) {
  return useQuery({
    queryKey: ideKeys.session(sessionId),
    queryFn: ({ signal }) => fetchSession(sessionId, signal),
    ...liveOptions,
  });
}
