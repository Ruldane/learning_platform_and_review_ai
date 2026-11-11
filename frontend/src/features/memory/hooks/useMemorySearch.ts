import { useMutation } from "@tanstack/react-query";
import { searchMemory } from "../api";
import { toHit } from "../toView";
import type { MemoryKindView, SearchResponse } from "../types";

interface SearchVariables {
  query: string;
  kinds: MemoryKindView[];
  /** Absent : 8 résultats. */
  k?: number;
}

function toResult(response: SearchResponse) {
  return { hits: response.hits.map(toHit), agentText: response.agent_text };
}

/**
 * Recherche sémantique (`POST /memory/search`). Une mutation et non une requête : la requête de
 * l'utilisateur n'entre ni dans une clé ni dans le cache, et chaque lancement refait l'appel.
 */
export function useMemorySearch() {
  return useMutation({
    gcTime: 0,
    mutationFn: async ({ query, kinds, k }: SearchVariables) =>
      toResult(await searchMemory(query, kinds, k)),
  });
}
