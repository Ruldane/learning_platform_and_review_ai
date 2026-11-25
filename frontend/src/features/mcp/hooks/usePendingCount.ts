import { useQuery } from "@tanstack/react-query";
import { fetchConfirmations } from "../api";
import { mcpKeys } from "../queryKeys";
import { isOpen } from "../toView";
import type { McpConfirmationOut } from "../types";

/** A request arrives while Claude works: the count is re-read every minute. */
const REFRESH_MS = 60_000;

const countOpen = (confirmations: McpConfirmationOut[]) => {
  const now = new Date();
  return confirmations.filter((confirmation) => isOpen(confirmation, now)).length;
};

/**
 * The number of requests still open, for the top bar: reading the requests, so
 * shared with the page. `undefined` until it is known (or on failure).
 */
export function usePendingCount(): number | undefined {
  return useQuery({
    queryKey: mcpKeys.confirmations,
    queryFn: ({ signal }) => fetchConfirmations(signal),
    select: countOpen,
    refetchInterval: REFRESH_MS,
  }).data;
}
