import { useQuery } from "@tanstack/react-query";
import { useCallback } from "react";
import { ApiError } from "@/shared/api/errors";
import { fetchInterviews } from "../api";
import { applicationsKeys } from "../queryKeys";
import { toInterviewView } from "../toInterviewView";
import type { InterviewOut } from "../types";

/**
 * `GET /interviews`: the interviews of a record, or (`null`) those without a record, most recent
 * first. An unknown record (404) is not re-read.
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
