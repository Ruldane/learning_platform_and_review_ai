import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { fetchCommittee } from "../api";
import { applicationsKeys } from "../queryKeys";
import { toCommitteeView } from "../toCommitteeView";

/** Tant que le comité délibère, la page relit aussi toute seule : une fin de session perdue ne bloque rien. */
const POLL_MS = 5_000;

/** `GET /committee/{id}` : l'exécution, ses votes, son verdict et son avant / après ; lue seulement quand elle est suivie. */
export function useCommittee(runId: string | null) {
  return useQuery({
    queryKey: applicationsKeys.committee(runId ?? ""),
    queryFn: ({ signal }) => fetchCommittee(runId ?? "", signal),
    select: toCommitteeView,
    enabled: runId !== null,
    refetchInterval: (query) => (query.state.data?.status === "running" ? POLL_MS : false),
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 1,
  });
}
