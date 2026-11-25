import { useQuery } from "@tanstack/react-query";
import { fetchAgents } from "../api";
import { settingsKeys } from "../queryKeys";

/**
 * Agents whose model can be overridden (`GET /settings/agents`); read only if
 * `enabled`.
 */
export function useAgents(enabled = true) {
  return useQuery({
    queryKey: settingsKeys.agents,
    queryFn: ({ signal }) => fetchAgents(signal),
    enabled,
  });
}
