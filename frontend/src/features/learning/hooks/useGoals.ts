import { useQuery } from "@tanstack/react-query";
import { fetchGoals } from "../api";
import { learningKeys } from "../queryKeys";
import { newestFirst } from "../toView";

/** Les objectifs (`GET /goals`), du plus récent au plus ancien. */
export function useGoals() {
  return useQuery({
    queryKey: learningKeys.goals,
    queryFn: ({ signal }) => fetchGoals(signal),
    select: newestFirst,
  });
}
