import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { fetchActivity } from "../api";
import type { ActivityItemView } from "../components/viewTypes";
import { homeKeys } from "../queryKeys";
import { toActivityView } from "../toView";

/** Événements par page (le serveur en plafonne 50). */
export const ACTIVITY_PAGE = 20;

function distinct(items: ActivityItemView[]): ActivityItemView[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    if (seen.has(item.id)) return false;
    seen.add(item.id);
    return true;
  });
}

/**
 * Le fil d'activité : la première page est relue (par les notifications de fond) ; « Voir plus »
 * lit la page plus ancienne avec le couple `before` + `before_id` du dernier événement montré. Un
 * événement n'est jamais montré deux fois (`id` stable) : les pages anciennes déjà lues restent
 * quand la première est relue.
 */
export function useActivity() {
  const first = useQuery({
    queryKey: homeKeys.activity,
    queryFn: ({ signal }) => fetchActivity({ limit: ACTIVITY_PAGE }, signal),
    select: (page) => page.items.map(toActivityView),
    staleTime: 0,
  });
  const [older, setOlder] = useState<ActivityItemView[]>([]);
  const [olderFull, setOlderFull] = useState<boolean | null>(null);
  const items = useMemo(() => distinct([...(first.data ?? []), ...older]), [first.data, older]);
  const more = useMutation({
    mutationFn: (last: ActivityItemView) =>
      fetchActivity({ before: last.at, beforeId: last.id, limit: ACTIVITY_PAGE }),
    onSuccess: (page) => {
      setOlder((previous) => [...previous, ...page.items.map(toActivityView)]);
      setOlderFull(page.items.length >= ACTIVITY_PAGE);
    },
  });
  const hasMore = olderFull ?? (first.data?.length ?? 0) >= ACTIVITY_PAGE;
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
