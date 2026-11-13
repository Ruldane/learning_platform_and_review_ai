import { useInfiniteQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { fetchJournal } from "../api";
import type { JournalEntryView } from "../components/viewTypes";
import { captureKeys } from "../queryKeys";
import { toEntryView } from "../toView";
import type { JournalKind } from "../types";

/** Entrées par page (le contrat accepte 1 à 100). */
export const JOURNAL_PAGE = 50;

/**
 * Le journal, filtré par type, page après page : la suivante part de `next_before` de la
 * précédente, jusqu'à ce que le serveur n'en rende plus.
 */
export function useJournal(kind: JournalKind | null) {
  const query = useInfiniteQuery({
    queryKey: captureKeys.journal(kind),
    initialPageParam: null as string | null,
    queryFn: ({ pageParam, signal }) =>
      fetchJournal({ kind, before: pageParam, limit: JOURNAL_PAGE }, signal),
    getNextPageParam: (last) => last.next_before ?? undefined,
    staleTime: 0,
  });
  const entries = useMemo<JournalEntryView[]>(
    () => query.data?.pages.flatMap((page) => page.entries.map(toEntryView)) ?? [],
    [query.data],
  );
  return { query, entries };
}
