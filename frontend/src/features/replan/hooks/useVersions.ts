import { useQuery } from "@tanstack/react-query";
import { fetchVersions } from "../api";
import { replanKeys } from "../queryKeys";

/** The plan's history (`GET /programs/{id}/versions`), re-read on each proposal and at each end. */
export function useVersions(programId: string) {
  return useQuery({
    queryKey: replanKeys.versions(programId),
    queryFn: ({ signal }) => fetchVersions(programId, signal),
    staleTime: 0,
  });
}
