import { useMutation, useQueryClient } from "@tanstack/react-query";
import { undoChange } from "../api";
import { useIdAction } from "./useIdAction";

/** Annule les changements d'un appel ; les lignes remises en état peuvent s'afficher ailleurs. */
export function useUndoChange() {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: undoChange,
    onSettled: () => queryClient.invalidateQueries(),
  });
  return useIdAction(mutation.mutateAsync);
}
