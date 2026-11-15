import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { fetchKit } from "../api";
import { applicationsKeys } from "../queryKeys";
import { toKitView } from "../toView";

/** Tant qu'un kit tourne, la page relit aussi toute seule : un `artifact.ready` perdu ne bloque rien. */
const POLL_MS = 10_000;

/**
 * `GET /applications/{id}/kit` : les sept pièces (`pending` pour celles pas encore rangées). Les
 * événements du flux ne font que dire quand relire : l'état vient toujours de cette lecture.
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
