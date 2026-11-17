import { useQuery } from "@tanstack/react-query";
import { fetchCosts } from "../api";
import type { CostWindow } from "../components/viewTypes";
import { costsKeys } from "../queryKeys";
import { toCostsView } from "../toView";

/** Le rapport des coûts d'une fenêtre ; changer de fenêtre relit (une clé par fenêtre). */
export function useCosts(days: CostWindow) {
  return useQuery({
    queryKey: costsKeys.report(days),
    queryFn: ({ signal }) => fetchCosts(days, signal),
    select: toCostsView,
  });
}
