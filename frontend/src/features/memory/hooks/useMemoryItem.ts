import { useQuery } from "@tanstack/react-query";
import { fetchItem } from "../api";
import { memoryKeys } from "../queryKeys";
import { toItemDetail } from "../toView";

/** Détail d'un élément (`GET /memory/items/{id}`) ; sans identifiant, aucun appel. */
export function useMemoryItem(id: string | null) {
  return useQuery({
    queryKey: memoryKeys.item(id ?? ""),
    queryFn: ({ signal }) => fetchItem(id ?? "", signal),
    enabled: id !== null,
    select: toItemDetail,
  });
}
