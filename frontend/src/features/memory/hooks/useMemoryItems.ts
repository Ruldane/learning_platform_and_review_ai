import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { fetchItems } from "../api";
import { memoryKeys } from "../queryKeys";
import { toItemRow } from "../toView";
import type { ItemsQuery, MemoryItemList } from "../types";

/** Une page d'éléments (`GET /memory/items`) ; la page précédente reste affichée pendant le changement. */
export function useMemoryItems(query: ItemsQuery) {
  return useQuery({
    queryKey: memoryKeys.items(query.filters, query.offset, query.status, query.limit),
    queryFn: ({ signal }) => fetchItems(query, signal),
    placeholderData: keepPreviousData,
    select: (data: MemoryItemList) => ({ items: data.items.map(toItemRow), total: data.total }),
  });
}
