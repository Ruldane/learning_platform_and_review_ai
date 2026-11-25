import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { fetchProject } from "../api";
import { projectKeys } from "../queryKeys";
import { toDetailView } from "../toView";

/** While a brief or evaluation runs, the page re-reads the project too, so a lost event is fine. */
const POLL_MS = 5_000;

const isMissing = (error: unknown) => error instanceof ApiError && error.status === 404;

/**
 * A project (`GET /projects/{id}`). Its status follows the server session: the page re-reads
 * on each session state change (`useProjectRun`) and, as a fallback, every 5 s while it is
 * `brief_pending` or `reviewing`.
 */
export function useProject(projectId: string) {
  const query = useQuery({
    queryKey: projectKeys.one(projectId),
    queryFn: ({ signal }) => fetchProject(projectId, signal),
    select: toDetailView,
    staleTime: 0,
    refetchInterval: (state) => {
      const status = state.state.data?.status;
      return status === "reviewing" || status === "brief_pending" ? POLL_MS : false;
    },
    retry: (count, error) => !isMissing(error) && count < 1,
  });
  return { query, missing: isMissing(query.error) };
}
