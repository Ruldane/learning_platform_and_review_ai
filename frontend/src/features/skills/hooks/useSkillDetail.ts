import { useQuery } from "@tanstack/react-query";
import { fetchSkillDetail } from "../api";
import { skillKeys } from "../queryKeys";

/** The detail of the open skill (`null`: nothing open, no request). */
export function useSkillDetail(skillId: string | null) {
  return useQuery({
    queryKey: skillKeys.detail(skillId ?? "none"),
    queryFn: ({ signal }) => fetchSkillDetail(skillId ?? "", signal),
    enabled: skillId !== null,
    staleTime: 0,
  });
}
