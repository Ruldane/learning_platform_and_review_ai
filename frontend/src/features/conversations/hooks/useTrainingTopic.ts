import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";

const idPattern = /^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/i;

export function trainingSkillId(value: string | null) {
  return value && idPattern.test(value) ? value : "";
}

export function useTrainingTopic(id: string) {
  return useQuery({
    queryKey: ["training", "skill-topic", id],
    enabled: Boolean(id),
    queryFn: async ({ signal }) => {
      const result = await api.GET("/skills/{skill_id}", {
        params: { path: { skill_id: id } },
        signal,
      });
      return unwrap(result).name;
    },
  });
}
