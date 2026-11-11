import type { ItemFilterValue } from "./components/viewTypes";
import type { ItemStatus } from "./types";

/**
 * Clés TanStack Query de la feature. Jamais de contenu : ni texte de document, ni requête de
 * recherche (la recherche est une mutation), seulement des filtres et des identifiants.
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
} as const;
