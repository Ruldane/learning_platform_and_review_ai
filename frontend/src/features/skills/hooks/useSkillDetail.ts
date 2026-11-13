import { useQuery } from "@tanstack/react-query";
import { fetchSkillDetail } from "../api";
import { skillKeys } from "../queryKeys";

/** Le détail de la compétence ouverte (`null` : rien d'ouvert, aucune requête). */
export function useSkillDetail(skillId: string | null) {
  return useQuery({
    queryKey: skillKeys.detail(skillId ?? "none"),
    queryFn: ({ signal }) => fetchSkillDetail(skillId ?? "", signal),
    enabled: skillId !== null,
    staleTime: 0,
  });
}
