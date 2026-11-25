import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createToken } from "../api";
import { mcpKeys } from "../queryKeys";

/**
 * Creates a token. Its value lives only in the mutation result (in memory, never in the read
 * cache nor in browser storage): `reset` forgets it once copied.
 */
export function useCreateToken() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createToken,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: mcpKeys.tokens }),
  });
}
