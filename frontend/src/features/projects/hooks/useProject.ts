import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { fetchProject } from "../api";
import { projectKeys } from "../queryKeys";
import { toDetailView } from "../toView";

/** Tant qu'un énoncé s'écrit ou qu'un rendu s'évalue, la page relit aussi le projet toute seule : un événement perdu ne bloque rien. */
const POLL_MS = 5_000;

const isMissing = (error: unknown) => error instanceof ApiError && error.status === 404;

/**
 * Un projet (`GET /projects/{id}`). Son statut suit la session du serveur : la page relit le projet
 * à chaque changement d'état de la session (`useProjectRun`) et, en repli, toutes les 5 s tant qu'il
 * est `brief_pending` ou `reviewing`.
 */
export function useProject(projectId: string) {
  const query = useQuery({
    queryKey: projectKeys.one(projectId),
    queryFn: ({ signal }) => fetchProject(projectId, signal),
    select: toDetailView,
    staleTime: 0,
    refetchInterval: (state) => {
      const status = state.state.data?.status;
      return status === "reviewing" || status === "brief_pending" ? POLL_MS : false;
    },
    retry: (count, error) => !isMissing(error) && count < 1,
  });
  return { query, missing: isMissing(query.error) };
}
