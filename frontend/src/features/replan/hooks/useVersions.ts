import { useQuery } from "@tanstack/react-query";
import { fetchVersions } from "../api";
import { replanKeys } from "../queryKeys";

/** L'historique du plan (`GET /programs/{id}/versions`), relu à chaque proposition et à chaque fin. */
export function useVersions(programId: string) {
  return useQuery({
    queryKey: replanKeys.versions(programId),
    queryFn: ({ signal }) => fetchVersions(programId, signal),
    staleTime: 0,
  });
}
