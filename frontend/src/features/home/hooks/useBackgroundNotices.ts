import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { fetchActivity, type ActivityQuery } from "../api";
import type { ActivityKind } from "../components/viewTypes";
import { homeKeys } from "../queryKeys";
import { toActivityView } from "../toView";
import { useNoticeQueue } from "./useNoticeQueue";

/**
 * Relecture toutes les 60 s, 8 s par notification (en pause au survol et au focus), 10 événements
 * relus au plus à chaque fois, dont 3 au plus annoncés.
 */
export const NOTICE_POLL_MS = 60_000;
export const NOTICE_DISMISS_MS = 8_000;
const BATCH = 10;
const ANNOUNCED = 3;

/** Les genres qui méritent une notification : la mémoire des agents n'en fait pas. */
const NOTICE_KINDS: readonly ActivityKind[] = ["lesson", "radar", "brief", "project", "job_failed"];

interface Cursor {
  at: string;
  id: string;
}

export interface NoticeOptions {
  /** Délai de relecture et de disparition ; les valeurs par défaut sont celles de la spec (tests). */
  pollMs?: number;
  dismissMs?: number;
}

/**
 * Les notifications de fond (P16). Au montage, le « dernier vu » est l'événement le plus récent du
 * fil (rien n'est annoncé de ce qui existait déjà) ; ensuite `GET /activity` est relu avec le
 * couple `after` + `after_id` toutes les `pollMs`, onglet visible seulement. Un nouvel événement
 * d'un genre gardé devient une notification (3 à l'écran, `dismissMs` chacune) et le brief comme le
 * fil sont relus. Après une longue absence, une rafale n'annonce que les 3 plus récents, le plus
 * récent d'abord : les autres sont dans le fil. Tout reste en mémoire : un rechargement repart du plus récent.
 */
export function useBackgroundNotices({
  pollMs = NOTICE_POLL_MS,
  dismissMs = NOTICE_DISMISS_MS,
}: NoticeOptions = {}) {
  const client = useQueryClient();
  const queue = useNoticeQueue(dismissMs);
  const { push } = queue;
  const cursor = useRef<Cursor | null>(null);
  const seeded = useRef(false);
  const shown = useRef(new Set<string>());

  useQuery({
    queryKey: homeKeys.notices,
    queryFn: async ({ signal }) => {
      const query: ActivityQuery = seeded.current
        ? { after: cursor.current?.at, afterId: cursor.current?.id, limit: BATCH }
        : { limit: 1 };
      const items = (await fetchActivity(query, signal)).items.map(toActivityView);
      const newest = items[0];
      if (newest) cursor.current = { at: newest.at, id: newest.id };
      if (!seeded.current) {
        seeded.current = true;
        return 0;
      }
      if (items.length === 0) return 0;
      const fresh = items.filter(
        (item) => NOTICE_KINDS.includes(item.kind) && !shown.current.has(item.id),
      );
      for (const item of fresh) shown.current.add(item.id);
      if (fresh.length > 0) {
        const latest = fresh.slice(0, ANNOUNCED);
        push(latest.map((item) => ({ id: item.id, title: item.title, detail: item.detail })));
        void client.invalidateQueries({ queryKey: homeKeys.brief });
      }
      void client.invalidateQueries({ queryKey: homeKeys.activity });
      return fresh.length;
    },
    refetchInterval: pollMs,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
    retry: false,
  });

  return { notices: queue.notices, dismiss: queue.dismiss, hold: queue.hold };
}
