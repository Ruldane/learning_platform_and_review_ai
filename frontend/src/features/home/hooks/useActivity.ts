import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { fetchActivity } from "../api";
import type { ActivityItemView } from "../components/viewTypes";
import { homeKeys } from "../queryKeys";
import { toActivityView } from "../toView";
import type { ActivityPage } from "../types";

/** Events per page (the server caps it at 50). */
export const ACTIVITY_PAGE = 20;

const selectItems = (page: ActivityPage) => page.items.map(toActivityView);

function distinct(items: ActivityItemView[]): ActivityItemView[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    if (seen.has(item.id)) return false;
    seen.add(item.id);
    return true;
  });
}

interface Feed {
  /** All events shown, newest first, with no gap. */
  items: ActivityItemView[];
  /** The last older page read was full; `null` until one has been read. */
  olderFull: boolean | null;
}

/**
 * Puts the re-read first page on the list already shown: its new events go to the top,
 * the rest (older pages read by « Voir plus » included) is kept as is. If none
 * event of the re-read page was already shown, more than 20 events have arrived since: the
 * list would keep a gap between the page and what follows, so it restarts from the first page.
 */
function mergeHead(feed: Feed, head: ActivityItemView[]): Feed {
  if (feed.items.length === 0) return { items: head, olderFull: null };
  const known = new Set(feed.items.map((item) => item.id));
  if (!head.some((item) => known.has(item.id))) return { items: head, olderFull: null };
  return { items: distinct([...head, ...feed.items]), olderFull: feed.olderFull };
}

/**
 * The activity feed: the first page is re-read (by the background notices) and its new items
 * go to the top of the list; « Voir plus » reads the older page with the `before` +
 * `before_id` pair of the last event shown. The list stays continuous: a re-read never removes
 * an event between two pages, and an event is never shown twice.
 */
export function useActivity() {
  const first = useQuery({
    queryKey: homeKeys.activity,
    queryFn: ({ signal }) => fetchActivity({ limit: ACTIVITY_PAGE }, signal),
    select: selectItems,
    staleTime: 0,
  });
  const [feed, setFeed] = useState<Feed>({ items: [], olderFull: null });
  const [seen, setSeen] = useState<ActivityItemView[] | undefined>(undefined);
  const head = first.data;
  if (head && head !== seen) {
    setSeen(head);
    setFeed((previous) => mergeHead(previous, head));
  }
  const more = useMutation({
    mutationFn: (last: ActivityItemView) =>
      fetchActivity({ before: last.at, beforeId: last.id, limit: ACTIVITY_PAGE }),
    onSuccess: (page) => {
      setFeed((previous) => ({
        items: distinct([...previous.items, ...page.items.map(toActivityView)]),
        olderFull: page.items.length >= ACTIVITY_PAGE,
      }));
    },
  });
  // First render with the page: `feed` has not yet taken `head` (state is set during this render).
  const items = feed.items.length === 0 && head ? head : feed.items;
  const hasMore = feed.olderFull ?? (head?.length ?? 0) >= ACTIVITY_PAGE;
  const last = items.at(-1);
  return {
    query: first,
    items,
    hasMore,
    loadMore: () => {
      if (last && !more.isPending) more.mutate(last);
    },
    loadingMore: more.isPending,
    moreError: more.isError ? more.error : null,
  };
}
