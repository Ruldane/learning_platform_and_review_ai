import { useQuery } from "@tanstack/react-query";
import { fetchSkillHistory } from "../api";
import { skillKeys } from "../queryKeys";

/** Semaines de la courbe de progression (le contrat accepte 1 à 52). */
export const HISTORY_WEEKS = 12;

/** Les relevés des 12 dernières semaines, lus seulement quand l'onglet Progression est ouvert. */
export function useSkillHistory(enabled: boolean) {
  return useQuery({
    queryKey: skillKeys.history(HISTORY_WEEKS),
    queryFn: ({ signal }) => fetchSkillHistory(HISTORY_WEEKS, signal),
    enabled,
    staleTime: 0,
  });
}
