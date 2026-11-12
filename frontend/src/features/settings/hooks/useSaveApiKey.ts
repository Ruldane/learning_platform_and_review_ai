import { useMutation, useQueryClient } from "@tanstack/react-query";
import { postApiKey } from "../api";
import { settingsKeys } from "../queryKeys";

/**
 * Enregistre la clé d'un fournisseur. La clé n'existe que dans les variables de la mutation :
 * ni clé de requête, ni cache, ni URL. `has_key` change, donc les modèles sont rechargés.
 */
export function useSaveApiKey() {
  const queryClient = useQueryClient();
  return useMutation({
    // Pas de conservation : la mutation (et la clé de ses variables) quitte le cache dès `reset()`.
    gcTime: 0,
    mutationFn: ({ provider, key }: { provider: string; key: string }) => postApiKey(provider, key),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: settingsKeys.apiKeys }),
        queryClient.invalidateQueries({ queryKey: settingsKeys.models }),
        // La clé Brave change `has_key` du compteur de la recherche web.
        queryClient.invalidateQueries({ queryKey: settingsKeys.searchUsage }),
      ]),
  });
}
