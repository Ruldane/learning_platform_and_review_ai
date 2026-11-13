import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { fetchSkillCompare } from "../api";
import { skillKeys } from "../queryKeys";

/** Un 404 est une réponse (pas d'objectif avec programme) : inutile de la redemander. */
const retryUnlessMissing = (count: number, error: Error) =>
  !(error instanceof ApiError && error.status === 404) && count < 1;

/** La comparaison avec le poste cible, lue seulement quand l'onglet Comparaison est ouvert. */
export function useSkillCompare(enabled: boolean) {
  return useQuery({
    queryKey: skillKeys.compare,
    queryFn: ({ signal }) => fetchSkillCompare(signal),
    enabled,
    staleTime: 0,
    retry: retryUnlessMissing,
  });
}
