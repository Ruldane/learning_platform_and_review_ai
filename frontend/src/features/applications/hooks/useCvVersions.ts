import { useQuery } from "@tanstack/react-query";
import { fetchCvVersions } from "../api";
import { applicationsKeys } from "../queryKeys";
import type { CvVersionOut } from "../types";

/** A CV version the committee can judge: its PDF is rendered. */
export interface ReadyVersion {
  id: string;
  number: number;
}

/** The ready versions, most recent first (`version_not_ready` for any other). */
export const readyVersions = (versions: CvVersionOut[]): ReadyVersion[] =>
  versions
    .filter((version) => version.status === "ready")
    .map(({ id, number }) => ({ id, number }))
    .sort((a, b) => b.number - a.number);

/** `GET /cv/versions?posting_id=`: the ready versions of the posting's CV. */
export function useCvVersions(postingId: string | null) {
  return useQuery({
    queryKey: applicationsKeys.cvVersions(postingId ?? ""),
    queryFn: ({ signal }) => fetchCvVersions(postingId ?? "", signal),
    select: readyVersions,
    enabled: postingId !== null,
  });
}
