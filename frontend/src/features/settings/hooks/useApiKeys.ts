import { useQuery } from "@tanstack/react-query";
import { fetchApiKeys } from "../api";
import { settingsKeys } from "../queryKeys";

/** Une entrée par fournisseur : origine de la clé et 4 derniers caractères, jamais la clé. */
export function useApiKeys() {
  return useQuery({
    queryKey: settingsKeys.apiKeys,
    queryFn: ({ signal }) => fetchApiKeys(signal),
  });
}
