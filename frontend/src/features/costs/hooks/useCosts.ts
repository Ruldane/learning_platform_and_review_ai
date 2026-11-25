import { useQuery } from "@tanstack/react-query";
import { fetchCosts } from "../api";
import type { CostWindow } from "../components/viewTypes";
import { costsKeys } from "../queryKeys";
import { toCostsView } from "../toView";

/** The cost report of a window; changing the window re-reads it (one key per window). */
export function useCosts(days: CostWindow) {
  return useQuery({
    queryKey: costsKeys.report(days),
    queryFn: ({ signal }) => fetchCosts(days, signal),
    select: toCostsView,
  });
}
