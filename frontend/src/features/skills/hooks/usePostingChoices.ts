import { useQuery } from "@tanstack/react-query";
import { fetchPostingChoices } from "../api";
import { skillKeys } from "../queryKeys";

/** The offers to offer as the comparison target, read when « Une offre » is chosen. */
export function usePostingChoices(enabled: boolean) {
  return useQuery({
    queryKey: skillKeys.postings,
    queryFn: ({ signal }) => fetchPostingChoices(signal),
    enabled,
    staleTime: 0,
  });
}
