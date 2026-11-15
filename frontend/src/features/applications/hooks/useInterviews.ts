import { useQuery } from "@tanstack/react-query";
import { useCallback } from "react";
import { ApiError } from "@/shared/api/errors";
import { fetchInterviews } from "../api";
import { applicationsKeys } from "../queryKeys";
import { toInterviewView } from "../toInterviewView";
import type { InterviewOut } from "../types";

/**
 * `GET /interviews` : les entretiens d'une fiche, ou (`null`) ceux sans fiche, le plus récent
 * d'abord. Une fiche inconnue (404) ne se relit pas.
 */
export function useInterviews(applicationId: string | null) {
  const select = useCallback(
    (rows: InterviewOut[]) =>
      (applicationId ? rows : rows.filter((row) => row.application_id === null)).map(
        toInterviewView,
      ),
    [applicationId],
  );
  return useQuery({
    queryKey: applicationsKeys.interviews(applicationId),
    queryFn: ({ signal }) => fetchInterviews(applicationId, signal),
    select,
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 1,
  });
}
