import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { fetchActivity } from "../api";
import type { ActivityItemView } from "../components/viewTypes";
import { homeKeys } from "../queryKeys";
import { toActivityView } from "../toView";
import type { ActivityPage } from "../types";

/** Événements par page (le serveur en plafonne 50). */
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
  /** Tous les événements montrés, du plus récent au plus ancien, sans trou. */
  items: ActivityItemView[];
  /** La dernière page plus ancienne lue était pleine ; `null` tant qu'aucune n'a été lue. */
  olderFull: boolean | null;
}

/**
 * Pose la première page relue sur la liste déjà montrée : ses événements nouveaux passent en tête,
 * le reste (pages plus anciennes lues par « Voir plus » comprises) est gardé tel quel. Si aucun
 * événement de la page relue n'était déjà montré, plus de 20 événements sont arrivés depuis : la
 * liste garderait un trou entre la page et ce qui la suit, on repart de la première page.
 */
function mergeHead(feed: Feed, head: ActivityItemView[]): Feed {
  if (feed.items.length === 0) return { items: head, olderFull: null };
  const known = new Set(feed.items.map((item) => item.id));
  if (!head.some((item) => known.has(item.id))) return { items: head, olderFull: null };
  return { items: distinct([...head, ...feed.items]), olderFull: feed.olderFull };
}

/**
 * Le fil d'activité : la première page est relue (par les notifications de fond) et ses nouveautés
 * se posent en tête de la liste ; « Voir plus » lit la page plus ancienne avec le couple `before` +
 * `before_id` du dernier événement montré. La liste est unique et continue : une relecture ne retire
 * jamais un événement d'entre deux pages, et un événement n'est jamais montré deux fois.
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
  // Au premier rendu avec la page, `feed` n'a pas encore pris `head` (l'état est posé pendant ce rendu).
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
