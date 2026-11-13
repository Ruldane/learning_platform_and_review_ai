import { useQuery } from "@tanstack/react-query";
import { fetchWaitingReplan } from "../api";
import { replanKeys } from "../queryKeys";

/** La replanification de ce programme qui attend une réponse : l'écran la rejoint après un rechargement. */
export function useWaitingReplan(programId: string) {
  return useQuery({
    queryKey: replanKeys.waiting(programId),
    queryFn: ({ signal }) => fetchWaitingReplan(programId, signal),
    staleTime: 0,
  });
}
