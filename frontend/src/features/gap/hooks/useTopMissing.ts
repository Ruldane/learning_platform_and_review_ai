import { useQuery } from "@tanstack/react-query";
import { fetchTopMissing } from "../api";
import { gapKeys } from "../queryKeys";

/** `GET /gap/top-missing` : les 10 compétences qui manquent le plus souvent dans les offres. */
export function useTopMissing() {
  return useQuery({
    queryKey: gapKeys.topMissing,
    queryFn: ({ signal }) => fetchTopMissing(signal),
    staleTime: 0,
  });
}
