import { useQuery } from "@tanstack/react-query";
import { fetchCommittees } from "../api";
import { applicationsKeys } from "../queryKeys";
import { toCommitteeView } from "../toCommitteeView";

/** `GET /committee?posting_id=` : les exécutions du comité de l'offre, la plus récente d'abord. */
export function useCommittees(postingId: string | null) {
  return useQuery({
    queryKey: applicationsKeys.committees(postingId ?? ""),
    queryFn: ({ signal }) => fetchCommittees(postingId ?? "", signal),
    select: (runs) => runs.map(toCommitteeView),
    enabled: postingId !== null,
  });
}
