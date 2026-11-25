import { keepPreviousData, useInfiniteQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { fetchJournal } from "../api";
import type { JournalEntryView } from "../components/viewTypes";
import { captureKeys } from "../queryKeys";
import { toEntryView } from "../toView";
import type { JournalKind } from "../types";

/** Entries per page (the contract accepts 1 to 100). */
export const JOURNAL_PAGE = 50;

/**
 * The journal, filtered by type, page after page: the next one starts from the `next_before` of the
 * previous one, until the server returns no more. When the type changes, the entries
 * shown stay until the new ones arrive: the list and its filter are not unmounted
 * (keyboard focus stays on the filter).
 */
export function useJournal(kind: JournalKind | null) {
  const query = useInfiniteQuery({
    queryKey: captureKeys.journal(kind),
    initialPageParam: null as string | null,
    queryFn: ({ pageParam, signal }) =>
      fetchJournal({ kind, before: pageParam, limit: JOURNAL_PAGE }, signal),
    getNextPageParam: (last) => last.next_before ?? undefined,
    staleTime: 0,
    placeholderData: keepPreviousData,
  });
  const entries = useMemo<JournalEntryView[]>(
    () => query.data?.pages.flatMap((page) => page.entries.map(toEntryView)) ?? [],
    [query.data],
  );
  return { query, entries };
}
