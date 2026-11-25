import { useQuery } from "@tanstack/react-query";
import { fetchMap } from "../api";
import { memoryKeys } from "../queryKeys";
import { toMapPoints } from "../toView";
import type { MapResponse } from "../types";

/** 2D map (`GET /memory/map`): the points, and whether the API kept only the newest. */
export function useMemoryMap() {
  return useQuery({
    queryKey: memoryKeys.map,
    queryFn: ({ signal }) => fetchMap(signal),
    select: (data: MapResponse) => ({ points: toMapPoints(data), truncated: data.truncated }),
  });
}
