import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { fetchSkillCompare } from "../api";
import { skillKeys } from "../queryKeys";

/** Un 404 est une réponse (pas d'objectif avec programme, écart pas rangé) : inutile de la redemander. */
const retryUnlessMissing = (count: number, error: Error) =>
  !(error instanceof ApiError && error.status === 404) && count < 1;

/**
 * La comparaison, lue seulement quand l'onglet Comparaison est ouvert : avec le poste cible de
 * l'objectif (`postingId` nul) ou avec une offre analysée.
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
