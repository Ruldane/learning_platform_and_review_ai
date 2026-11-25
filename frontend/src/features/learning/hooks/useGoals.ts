import { useQuery } from "@tanstack/react-query";
import { fetchGoals } from "../api";
import { learningKeys } from "../queryKeys";
import { newestFirst } from "../toView";

/** The goals (`GET /goals`), newest first. */
export function useGoals() {
  return useQuery({
    queryKey: learningKeys.goals,
    queryFn: ({ signal }) => fetchGoals(signal),
    select: newestFirst,
  });
}
