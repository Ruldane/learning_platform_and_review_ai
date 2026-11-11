import { useQuery } from "@tanstack/react-query";
import { fetchHealth } from "../api";

export const HEALTH_REFETCH_MS = 30_000;

/** État des services, rafraîchi toutes les 30 s (la requête est annulée si le composant part). */
export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => fetchHealth(signal),
    refetchInterval: HEALTH_REFETCH_MS,
    // Un serveur injoignable doit se voir tout de suite ; le prochain tour retente.
    retry: false,
  });
}
