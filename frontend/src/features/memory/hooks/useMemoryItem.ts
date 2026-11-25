import { useQuery } from "@tanstack/react-query";
import { fetchItem } from "../api";
import { memoryKeys } from "../queryKeys";
import { toItemDetail } from "../toView";

/** Detail of an item (`GET /memory/items/{id}`); without an id, no call. */
export function useMemoryItem(id: string | null) {
  return useQuery({
    queryKey: memoryKeys.item(id ?? ""),
    queryFn: ({ signal }) => fetchItem(id ?? "", signal),
    enabled: id !== null,
    select: toItemDetail,
  });
}
