import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deleteApiKey } from "../api";
import { settingsKeys } from "../queryKeys";

/** Supprime la clé saisie dans l'interface d'un fournisseur (`has_key` peut changer). */
export function useDeleteApiKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (provider: string) => deleteApiKey(provider),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: settingsKeys.apiKeys }),
        queryClient.invalidateQueries({ queryKey: settingsKeys.models }),
        // La clé Brave change `has_key` du compteur de la recherche web.
        queryClient.invalidateQueries({ queryKey: settingsKeys.searchUsage }),
      ]),
  });
}
