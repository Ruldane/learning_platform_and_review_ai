import { useInfiniteQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { fetchAgentCalls } from "../api";
import type { CallView } from "../components/viewTypes";
import { costsKeys } from "../queryKeys";
import { toCallView } from "../toView";

/** Calls per page (the contract accepts 1 to 100; 50 by default, P16). */
export const CALLS_PAGE = 50;

/**
 * The journal, page after page: the next one starts from the previous `next_before`. The filters
 * are part of the key: changing them starts again from the first page, without a cursor.
 */
export function useAgentCalls(agent: string | null, graph: string | null) {
  const query = useInfiniteQuery({
    queryKey: costsKeys.calls(agent, graph),
    initialPageParam: null as string | null,
    queryFn: ({ pageParam, signal }) =>
      fetchAgentCalls({ before: pageParam, limit: CALLS_PAGE, agent, graph }, signal),
    getNextPageParam: (last) => last.next_before ?? undefined,
    staleTime: 0,
    // Going back to an already seen filter starts from the first page (D188 n° 6): no page kept.
    gcTime: 0,
  });
  const calls = useMemo<CallView[]>(
    () => query.data?.pages.flatMap((page) => page.items.map(toCallView)) ?? [],
    [query.data],
  );
  return { query, calls };
}
