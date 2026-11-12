import { useQuery } from "@tanstack/react-query";
import { fetchSearchUsage } from "../api";
import { settingsKeys } from "../queryKeys";
import { toBraveUsageView } from "../userSettings";

/** Consommation Brave du mois (`GET /research/usage`), au format de la jauge. */
export function useSearchUsage() {
  return useQuery({
    queryKey: settingsKeys.searchUsage,
    queryFn: ({ signal }) => fetchSearchUsage(signal),
    select: toBraveUsageView,
  });
}
