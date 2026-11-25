import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { fetchKit } from "../api";
import { applicationsKeys } from "../queryKeys";
import { toKitView } from "../toView";

/** While a kit runs, the page also re-reads on its own: a lost `artifact.ready` blocks nothing. */
const POLL_MS = 10_000;

/**
 * `GET /applications/{id}/kit`: the seven pieces (`pending` for those not yet filed). The
 * stream events only say when to re-read: the state always comes from that read.
 */
export function useKit(applicationId: string) {
  return useQuery({
    queryKey: applicationsKeys.kit(applicationId),
    queryFn: ({ signal }) => fetchKit(applicationId, signal),
    select: toKitView,
    refetchInterval: (query) => (query.state.data?.running ? POLL_MS : false),
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 1,
  });
}
