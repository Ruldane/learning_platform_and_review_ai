import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { fetchInterview } from "../api";
import { applicationsKeys } from "../queryKeys";
import { toInterviewView } from "../toInterviewView";

/** While the interview runs, the page also re-reads on its own: a lost session end blocks
 * nothing. */
const POLL_MS = 5_000;

/** `GET /interviews/{id}`: the interview, its exchanges and its debrief. */
export function useInterview(interviewId: string) {
  return useQuery({
    queryKey: applicationsKeys.interview(interviewId),
    queryFn: ({ signal }) => fetchInterview(interviewId, signal),
    select: toInterviewView,
    refetchInterval: (query) => (query.state.data?.status === "running" ? POLL_MS : false),
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 1,
  });
}
