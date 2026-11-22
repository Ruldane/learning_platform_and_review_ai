import { useMutation, useQueryClient } from "@tanstack/react-query";
import { putEnabled } from "../api";
import { mcpKeys } from "../queryKeys";

/** Allume ou coupe l'accès MCP ; l'écran suit la réponse du serveur. */
export function useSetMcpEnabled() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (enabled: boolean) => putEnabled(enabled),
    onSuccess: (settings) => {
      queryClient.setQueryData(mcpKeys.settings, settings);
      return queryClient.invalidateQueries({ queryKey: mcpKeys.relay });
    },
  });
}
