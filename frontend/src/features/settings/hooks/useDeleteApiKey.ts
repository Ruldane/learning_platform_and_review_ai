import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deleteApiKey } from "../api";
import { settingsKeys } from "../queryKeys";

/** Deletes the key entered in the interface for a provider (`has_key` may change). */
export function useDeleteApiKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (provider: string) => deleteApiKey(provider),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: settingsKeys.apiKeys }),
        queryClient.invalidateQueries({ queryKey: settingsKeys.models }),
        // The Brave key changes `has_key` of the web search counter.
        queryClient.invalidateQueries({ queryKey: settingsKeys.searchUsage }),
      ]),
  });
}
