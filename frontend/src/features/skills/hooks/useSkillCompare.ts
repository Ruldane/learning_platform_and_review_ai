import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { fetchSkillCompare } from "../api";
import { skillKeys } from "../queryKeys";

/** A 404 is an answer (no goal with a program, gap not filed): no need to ask again. */
const retryUnlessMissing = (count: number, error: Error) =>
  !(error instanceof ApiError && error.status === 404) && count < 1;

/**
 * The comparison, read only when the Comparison tab is open: with the goal's target
 * role (`postingId` null) or with an analyzed offer.
 */
export function useSkillCompare(enabled: boolean, postingId: string | null = null) {
  return useQuery({
    queryKey: skillKeys.compare(postingId),
    queryFn: ({ signal }) =>
      fetchSkillCompare(
        postingId === null ? { kind: "goal" } : { kind: "posting", postingId },
        signal,
      ),
    enabled,
    staleTime: 0,
    retry: retryUnlessMissing,
  });
}
