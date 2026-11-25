import { useMutation, useQueryClient } from "@tanstack/react-query";
import { putEnabled } from "../api";
import { mcpKeys } from "../queryKeys";

/** Turns MCP access on or off; the screen follows the server's answer. */
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
