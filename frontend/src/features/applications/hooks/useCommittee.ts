import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { fetchCommittee } from "../api";
import { applicationsKeys } from "../queryKeys";
import { toCommitteeView } from "../toCommitteeView";

/** While the committee deliberates, the page also re-reads on its own: a lost session end blocks
 * nothing. */
const POLL_MS = 5_000;

/** `GET /committee/{id}`: the run, its votes, its verdict and its before / after; read only while
 * it is followed. */
export function useCommittee(runId: string | null) {
  return useQuery({
    queryKey: applicationsKeys.committee(runId ?? ""),
    queryFn: ({ signal }) => fetchCommittee(runId ?? "", signal),
    select: toCommitteeView,
    enabled: runId !== null,
    refetchInterval: (query) => (query.state.data?.status === "running" ? POLL_MS : false),
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 1,
  });
}
