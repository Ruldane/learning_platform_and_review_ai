import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { fetchActions } from "../api";
import type { ActionView } from "../components/viewTypes";
import { mcpKeys } from "../queryKeys";
import { toActionView } from "../toView";

/** La table des outils et de leurs niveaux (`GET /mcp/actions`). */
export function useMcpActions() {
  const query = useQuery({
    queryKey: mcpKeys.actions,
    queryFn: ({ signal }) => fetchActions(signal),
  });
  const actions = useMemo<ActionView[]>(() => query.data?.map(toActionView) ?? [], [query.data]);
  return { query, actions };
}
