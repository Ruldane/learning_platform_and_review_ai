import { useQuery } from "@tanstack/react-query";
import { fetchUsage } from "../api";
import { ideKeys } from "../queryKeys";

/** Les jetons du professeur pour la séance et le jour (`GET /ide/usage`). */
export function useUsage(sessionId: string) {
  return useQuery({
    queryKey: ideKeys.usage(sessionId),
    queryFn: ({ signal }) => fetchUsage(sessionId, signal),
  });
}
