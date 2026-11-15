import { useQuery } from "@tanstack/react-query";
import { fetchCvVersions } from "../api";
import { applicationsKeys } from "../queryKeys";
import type { CvVersionOut } from "../types";

/** Une version de CV que le comité peut juger : son PDF est rendu. */
export interface ReadyVersion {
  id: string;
  number: number;
}

/** Les versions prêtes, la plus récente d'abord (`version_not_ready` pour toute autre). */
export const readyVersions = (versions: CvVersionOut[]): ReadyVersion[] =>
  versions
    .filter((version) => version.status === "ready")
    .map(({ id, number }) => ({ id, number }))
    .sort((a, b) => b.number - a.number);

/** `GET /cv/versions?posting_id=` : les versions prêtes du CV de l'offre. */
export function useCvVersions(postingId: string | null) {
  return useQuery({
    queryKey: applicationsKeys.cvVersions(postingId ?? ""),
    queryFn: ({ signal }) => fetchCvVersions(postingId ?? "", signal),
    select: readyVersions,
    enabled: postingId !== null,
  });
}
