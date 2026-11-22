import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { readBoss, startBoss, submitBoss } from "../api";

export function useBoss(id: string) {
  const queryKey = ["boss", id] as const;
  const cache = useQueryClient();
  const query = useQuery({
    queryKey,
    queryFn: ({ signal }) => readBoss(id, signal),
    refetchInterval: ({ state }) => {
      const attempt = state.data?.attempt;
      if (attempt?.state === "reviewing") return 750;
      return attempt?.state === "building" ? 3_000 : false;
    },
  });
  const start = useMutation({
    mutationFn: () => startBoss(id),
    onSettled: () => cache.invalidateQueries({ queryKey }),
  });
  const submit = useMutation({
    mutationFn: () => submitBoss(id),
    onSettled: () => cache.invalidateQueries({ queryKey }),
  });
  return { query, start, submit };
}
