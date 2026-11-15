import { useQuery } from "@tanstack/react-query";
import { fetchApplicationCheck } from "../api";
import { gapKeys } from "../queryKeys";

/** `GET /applications/check` : la candidature de l'offre et les fiches qui lui ressemblent. */
export function useApplicationCheck(postingId: string) {
  return useQuery({
    queryKey: gapKeys.applicationCheck(postingId),
    queryFn: ({ signal }) => fetchApplicationCheck(postingId, signal),
  });
}
