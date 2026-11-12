import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { fetchResources } from "../api";
import { lessonsKeys } from "../queryKeys";
import { toResourceView } from "../toView";
import type { LibraryFilterValue } from "../types";

/** La bibliothèque (`GET /resources`) selon les filtres ; l'ancienne liste reste affichée pendant le changement. */
export function useResources(filters: LibraryFilterValue) {
  return useQuery({
    queryKey: lessonsKeys.resources(filters),
    queryFn: ({ signal }) => fetchResources(filters, signal),
    select: (resources) => resources.map(toResourceView),
    placeholderData: keepPreviousData,
  });
}
