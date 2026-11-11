import { useQuery } from "@tanstack/react-query";
import { fetchMap } from "../api";
import { memoryKeys } from "../queryKeys";
import { toMapPoints } from "../toView";
import type { MapResponse } from "../types";

/** Carte 2D (`GET /memory/map`) : les points et si l'API n'a gardé que les plus récents. */
export function useMemoryMap() {
  return useQuery({
    queryKey: memoryKeys.map,
    queryFn: ({ signal }) => fetchMap(signal),
    select: (data: MapResponse) => ({ points: toMapPoints(data), truncated: data.truncated }),
  });
}
