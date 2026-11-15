import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { fetchApplication } from "../api";
import { applicationsKeys } from "../queryKeys";

/** `GET /applications/{id}` : la fiche ouverte ; une fiche inconnue (404) ne se relit pas. */
export function useApplication(applicationId: string) {
  return useQuery({
    queryKey: applicationsKeys.one(applicationId),
    queryFn: ({ signal }) => fetchApplication(applicationId, signal),
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 1,
  });
}
