import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { fetchCalls, fetchChanges } from "../api";
import type { CallView, ChangeView } from "../components/viewTypes";
import { mcpKeys } from "../queryKeys";
import { toCallView, toChangeView } from "../toView";
import { useTokens } from "./useTokens";

/** Le journal des appels et les changements annulables, lus ensemble. */
export function useHistory() {
  const calls = useQuery({ queryKey: mcpKeys.calls, queryFn: ({ signal }) => fetchCalls(signal) });
  const changes = useQuery({
    queryKey: mcpKeys.changes,
    queryFn: ({ signal }) => fetchChanges(signal),
  });
  const { query: tokenQuery } = useTokens();
  const callViews = useMemo<CallView[]>(() => {
    const labels = new Map(tokenQuery.data?.map((token) => [token.id, token.label]));
    return calls.data?.map((call) => toCallView(call, labels)) ?? [];
  }, [calls.data, tokenQuery.data]);
  const changeViews = useMemo<ChangeView[]>(
    () => changes.data?.map(toChangeView) ?? [],
    [changes.data],
  );
  return { calls, changes, callViews, changeViews };
}
