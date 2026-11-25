import { useMutation, useQueryClient } from "@tanstack/react-query";
import { decideConfirmation } from "../api";
import type { Decision } from "../types";
import { useIdAction } from "./useIdAction";

/**
 * Confirms or refuses a request, once per request. Confirming runs the requested action,
 * which may touch any feature: the displayed reads are then all re-read.
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
