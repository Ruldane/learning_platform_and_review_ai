import { useQuery } from "@tanstack/react-query";
import { fetchConfirmations } from "../api";
import { mcpKeys } from "../queryKeys";
import { isOpen } from "../toView";
import type { McpConfirmationOut } from "../types";

/** Une demande arrive quand Claude travaille : on relit le compte chaque minute. */
const REFRESH_MS = 60_000;

const countOpen = (confirmations: McpConfirmationOut[]) => {
  const now = new Date();
  return confirmations.filter((confirmation) => isOpen(confirmation, now)).length;
};

/**
 * Le nombre de demandes encore ouvertes, pour la barre du haut : la lecture des demandes, donc
 * partagée avec la page. `undefined` tant qu'il n'est pas connu (ou en cas de panne).
 */
export function usePendingCount(): number | undefined {
  return useQuery({
    queryKey: mcpKeys.confirmations,
    queryFn: ({ signal }) => fetchConfirmations(signal),
    select: countOpen,
    refetchInterval: REFRESH_MS,
  }).data;
}
