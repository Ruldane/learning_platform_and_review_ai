import { useQuery } from "@tanstack/react-query";
import { fetchTopMissing } from "../api";
import { gapKeys } from "../queryKeys";

/** `GET /gap/top-missing`: the 10 skills most often missing from postings. */
export function useTopMissing() {
  return useQuery({
    queryKey: gapKeys.topMissing,
    queryFn: ({ signal }) => fetchTopMissing(signal),
    staleTime: 0,
  });
}
