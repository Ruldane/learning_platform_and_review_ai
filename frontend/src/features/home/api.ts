import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";

/** `GET /brief/today`: the local day's brief, created on open if missing. */
export async function fetchBrief(signal?: AbortSignal) {
  return unwrap(await api.GET("/brief/today", { signal }));
}

/** Feed read bounds: the cursor is the pair `(at, id)`, never `at` alone. */
export interface ActivityQuery {
  /** Newer than the pair `(after, afterId)` (re-read). */
  after?: string;
  afterId?: string;
  /** Older than the pair `(before, beforeId)` (next page). */
  before?: string;
  beforeId?: string;
  limit?: number;
}

/**
 * `GET /activity`: events, newest first. The bounds are exclusive on the
 * pair `(at, id)`: sending `after` without `after_id` would lose or repeat the events that
 * share an instant.
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
