import { useQuery } from "@tanstack/react-query";
import { fetchCommittees } from "../api";
import { applicationsKeys } from "../queryKeys";
import { toCommitteeView } from "../toCommitteeView";

/** `GET /committee?posting_id=`: the committee runs for the posting, most recent first. */
export function useCommittees(postingId: string | null) {
  return useQuery({
    queryKey: applicationsKeys.committees(postingId ?? ""),
    queryFn: ({ signal }) => fetchCommittees(postingId ?? "", signal),
    select: (runs) => runs.map(toCommitteeView),
    enabled: postingId !== null,
  });
}
