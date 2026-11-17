import { useQuery } from "@tanstack/react-query";
import { fetchAgents } from "../api";
import { settingsKeys } from "../queryKeys";

/** Les agents dont on peut surcharger le modèle (`GET /settings/agents`) ; lus seulement si `enabled`. */
export function useAgents(enabled = true) {
  return useQuery({
    queryKey: settingsKeys.agents,
    queryFn: ({ signal }) => fetchAgents(signal),
    enabled,
  });
}
