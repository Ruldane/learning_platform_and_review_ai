import { useQuery } from "@tanstack/react-query";
import { fetchWaitingReplan } from "../api";
import { replanKeys } from "../queryKeys";

/** This program's replan waiting for an answer: the screen joins it after a reload. */
export function useWaitingReplan(programId: string) {
  return useQuery({
    queryKey: replanKeys.waiting(programId),
    queryFn: ({ signal }) => fetchWaitingReplan(programId, signal),
    staleTime: 0,
  });
}
