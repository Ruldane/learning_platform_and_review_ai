import { useMutation, useQueryClient } from "@tanstack/react-query";
import { revokeToken } from "../api";
import { mcpKeys } from "../queryKeys";
import { useIdAction } from "./useIdAction";

/** Révoque un jeton ; ses lignes d'historique restent. */
export function useRevokeToken() {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: revokeToken,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: mcpKeys.tokens }),
  });
  return useIdAction(mutation.mutateAsync);
}
