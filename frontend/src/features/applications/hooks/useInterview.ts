import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { fetchInterview } from "../api";
import { applicationsKeys } from "../queryKeys";
import { toInterviewView } from "../toInterviewView";

/** Tant que l'entretien tourne, la page relit aussi toute seule : une fin de session perdue ne bloque rien. */
const POLL_MS = 5_000;

/** `GET /interviews/{id}` : l'entretien, ses échanges et son débrief. */
export function useInterview(interviewId: string) {
  return useQuery({
    queryKey: applicationsKeys.interview(interviewId),
    queryFn: ({ signal }) => fetchInterview(interviewId, signal),
    select: toInterviewView,
    refetchInterval: (query) => (query.state.data?.status === "running" ? POLL_MS : false),
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 1,
  });
}
