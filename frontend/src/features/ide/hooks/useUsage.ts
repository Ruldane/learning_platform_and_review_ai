import { useQuery } from "@tanstack/react-query";
import { fetchUsage } from "../api";
import { ideKeys } from "../queryKeys";

/** The teacher's tokens for the session and the day (`GET /ide/usage`). */
export function useUsage(sessionId: string) {
  return useQuery({
    queryKey: ideKeys.usage(sessionId),
    queryFn: ({ signal }) => fetchUsage(sessionId, signal),
  });
}
