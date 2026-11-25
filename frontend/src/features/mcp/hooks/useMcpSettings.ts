import { useQuery } from "@tanstack/react-query";
import { fetchSettings } from "../api";
import { mcpKeys } from "../queryKeys";

/** The master switch (`GET /mcp/settings`). */
export function useMcpSettings() {
  return useQuery({
    queryKey: mcpKeys.settings,
    queryFn: ({ signal }) => fetchSettings(signal),
  });
}
