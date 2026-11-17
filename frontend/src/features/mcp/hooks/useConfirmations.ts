import { useQuery } from "@tanstack/react-query";
import { fetchConfirmations } from "../api";
import { mcpKeys } from "../queryKeys";

/** Les demandes « À confirmer » (`GET /mcp/confirmations`), en attente ou décidées. */
export function useConfirmations() {
  return useQuery({
    queryKey: mcpKeys.confirmations,
    queryFn: ({ signal }) => fetchConfirmations(signal),
  });
}
