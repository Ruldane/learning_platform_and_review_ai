import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";

/** `GET /brief/today` : le brief du jour local, créé à l'ouverture s'il manque. */
export async function fetchBrief(signal?: AbortSignal) {
  return unwrap(await api.GET("/brief/today", { signal }));
}

/** Les bornes d'une lecture du fil : le curseur est le couple `(at, id)`, jamais `at` seul. */
export interface ActivityQuery {
  /** Plus récents que le couple `(after, afterId)` (relecture). */
  after?: string;
  afterId?: string;
  /** Plus anciens que le couple `(before, beforeId)` (page suivante). */
  before?: string;
  beforeId?: string;
  limit?: number;
}

/**
 * `GET /activity` : les événements, le plus récent d'abord. Les bornes sont exclusives sur le
 * couple `(at, id)` : envoyer `after` sans `after_id` perdrait ou répéterait les événements qui
 * partagent un instant.
 */
export async function fetchActivity(query: ActivityQuery = {}, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/activity", {
      params: {
        query: {
          after: query.after,
          after_id: query.after ? query.afterId : undefined,
          before: query.before,
          before_id: query.before ? query.beforeId : undefined,
          limit: query.limit,
        },
      },
      signal,
    }),
  );
}
