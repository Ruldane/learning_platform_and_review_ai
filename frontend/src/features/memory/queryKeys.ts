import type { ItemFilterValue } from "./components/viewTypes";
import type { ItemStatus } from "./types";

/**
 * TanStack Query keys of the feature. Never content: no document text, no search
 * query (search is a mutation), only filters and identifiers.
 */
export const memoryKeys = {
  all: ["memory"],
  itemsAll: ["memory", "items"],
  items: (filters: ItemFilterValue, offset: number, status: ItemStatus, limit: number) =>
    ["memory", "items", status, filters, offset, limit] as const,
  item: (id: string) => ["memory", "item", id] as const,
  stats: ["memory", "stats"],
  map: ["memory", "map"],
  documents: ["memory", "documents"],
  runningLearnings: ["memory", "sessions", "learned_document", "running"],
} as const;
