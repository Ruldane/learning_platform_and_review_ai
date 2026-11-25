import { useMutation, useQueryClient } from "@tanstack/react-query";
import { postApiKey } from "../api";
import { settingsKeys } from "../queryKeys";

/**
 * Saves a provider's key. The key exists only in the mutation's variables:
 * not in a query key, cache, or URL. `has_key` changes, so the models are reloaded.
 */
export function useSaveApiKey() {
  const queryClient = useQueryClient();
  return useMutation({
    // No retention: the mutation (and its variables' key) leaves the cache on `reset()`.
    gcTime: 0,
    mutationFn: ({ provider, key }: { provider: string; key: string }) => postApiKey(provider, key),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: settingsKeys.apiKeys }),
        queryClient.invalidateQueries({ queryKey: settingsKeys.models }),
        // The Brave key changes `has_key` of the web search counter.
        queryClient.invalidateQueries({ queryKey: settingsKeys.searchUsage }),
      ]),
  });
}
