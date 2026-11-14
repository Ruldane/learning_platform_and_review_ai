import { useQuery } from "@tanstack/react-query";
import { fetchPostingChoices } from "../api";
import { skillKeys } from "../queryKeys";

/** Les offres à proposer comme cible de la comparaison, lues quand on choisit « Une offre ». */
export function usePostingChoices(enabled: boolean) {
  return useQuery({
    queryKey: skillKeys.postings,
    queryFn: ({ signal }) => fetchPostingChoices(signal),
    enabled,
    staleTime: 0,
  });
}
