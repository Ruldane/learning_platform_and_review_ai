import { useQuery } from "@tanstack/react-query";
import { fetchModels } from "../api";
import { settingsKeys } from "../queryKeys";

/** Fournisseurs (avec ou sans clé), modèles proposés et préréglages. */
export function useModels() {
  return useQuery({
    queryKey: settingsKeys.models,
    queryFn: ({ signal }) => fetchModels(signal),
  });
}
