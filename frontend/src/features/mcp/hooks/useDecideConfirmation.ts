import { useMutation, useQueryClient } from "@tanstack/react-query";
import { decideConfirmation } from "../api";
import type { Decision } from "../types";
import { useIdAction } from "./useIdAction";

/**
 * Confirme ou refuse une demande, une seule fois par demande. Confirmer exécute l'action demandée,
 * qui peut toucher n'importe quelle feature : on relit alors toutes les lectures affichées.
 */
export function useDecideConfirmation() {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: Decision }) =>
      decideConfirmation(id, decision),
    onSettled: () => queryClient.invalidateQueries(),
  });
  return useIdAction((id: string, decision: Decision) => mutation.mutateAsync({ id, decision }));
}
