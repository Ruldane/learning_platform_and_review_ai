import { useInfiniteQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { fetchAgentCalls } from "../api";
import type { CallView } from "../components/viewTypes";
import { costsKeys } from "../queryKeys";
import { toCallView } from "../toView";

/** Appels par page (le contrat accepte 1 à 100 ; 50 par défaut, P16). */
export const CALLS_PAGE = 50;

/**
 * Le journal, page après page : la suivante part de `next_before` de la précédente. Les filtres
 * font partie de la clé : en changer repart de la première page, sans curseur.
 */
export function useAgentCalls(agent: string | null, graph: string | null) {
  const query = useInfiniteQuery({
    queryKey: costsKeys.calls(agent, graph),
    initialPageParam: null as string | null,
    queryFn: ({ pageParam, signal }) =>
      fetchAgentCalls({ before: pageParam, limit: CALLS_PAGE, agent, graph }, signal),
    getNextPageParam: (last) => last.next_before ?? undefined,
    staleTime: 0,
  });
  const calls = useMemo<CallView[]>(
    () => query.data?.pages.flatMap((page) => page.items.map(toCallView)) ?? [],
    [query.data],
  );
  return { query, calls };
}
