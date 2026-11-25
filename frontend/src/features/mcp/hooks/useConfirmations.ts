import { useQuery } from "@tanstack/react-query";
import { fetchConfirmations } from "../api";
import { mcpKeys } from "../queryKeys";

/** The « À confirmer » requests (`GET /mcp/confirmations`), pending or decided. */
export function useConfirmations() {
  return useQuery({
    queryKey: mcpKeys.confirmations,
    queryFn: ({ signal }) => fetchConfirmations(signal),
  });
}
