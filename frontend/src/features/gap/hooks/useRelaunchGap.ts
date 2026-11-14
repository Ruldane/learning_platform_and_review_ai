import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { relaunchGap } from "../api";
import { gapKeys } from "../queryKeys";

/**
 * Relance l'analyse d'une offre (202). Une analyse déjà en cours (409 `gap_in_progress`) n'est pas
 * une erreur : on relit l'offre pour la suivre.
 */
export function useRelaunchGap(postingId: string, onRelaunched: () => void) {
  const client = useQueryClient();
  const refresh = () => {
    void client.invalidateQueries({ queryKey: gapKeys.posting(postingId) });
    void client.invalidateQueries({ queryKey: gapKeys.gap(postingId) });
    void client.invalidateQueries({ queryKey: gapKeys.postings });
    onRelaunched();
  };
  const mutation = useMutation({
    mutationFn: () => relaunchGap(postingId),
    onSuccess: refresh,
    onError: (failure) => {
      if (failure instanceof ApiError && failure.code === "gap_in_progress") refresh();
    },
  });
  const failure = mutation.error;
  const quiet = failure instanceof ApiError && failure.code === "gap_in_progress";
  return {
    relaunch: () => mutation.mutate(),
    pending: mutation.isPending,
    error: mutation.isError && !quiet ? errorMessage(failure) : null,
  };
}
