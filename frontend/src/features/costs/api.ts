import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { CostWindow } from "./components/viewTypes";

/** `GET /costs?days=` : 7, 30 ou 90 jours locaux (toute autre durée : 422). */
export async function fetchCosts(days: CostWindow, signal?: AbortSignal) {
  return unwrap(await api.GET("/costs", { params: { query: { days } }, signal }));
}

export interface CallsQuery {
  /** `next_before` de la page précédente. */
  before: string | null;
  limit: number;
  agent: string | null;
  graph: string | null;
}

/** `GET /costs/calls` : du plus récent au plus ancien, `next_before` pour la suite. */
export async function fetchAgentCalls(
  { before, limit, agent, graph }: CallsQuery,
  signal?: AbortSignal,
) {
  return unwrap(
    await api.GET("/costs/calls", {
      params: {
        query: {
          before: before ?? undefined,
          limit,
          agent: agent ?? undefined,
          graph: graph ?? undefined,
        },
      },
      signal,
    }),
  );
}
