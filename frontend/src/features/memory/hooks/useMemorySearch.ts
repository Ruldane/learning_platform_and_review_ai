import { useMutation } from "@tanstack/react-query";
import { searchMemory } from "../api";
import { toHit } from "../toView";
import type { MemoryKindView, SearchResponse } from "../types";

interface SearchVariables {
  query: string;
  kinds: MemoryKindView[];
  /** Absent: 8 results. */
  k?: number;
}

function toResult(response: SearchResponse) {
  return { hits: response.hits.map(toHit), agentText: response.agent_text };
}

/**
 * Semantic search (`POST /memory/search`). A mutation rather than a query: the user's query
 * enters neither a key nor the cache, and each run makes the call again.
 */
export function useMemorySearch() {
  return useMutation({
    gcTime: 0,
    mutationFn: async ({ query, kinds, k }: SearchVariables) =>
      toResult(await searchMemory(query, kinds, k)),
  });
}
